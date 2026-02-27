import asyncio
import logging
import os
import tempfile
from pathlib import Path

import discord
from discord import VoiceClient
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_MODEL = os.getenv("OPENAI_VOICE_MODEL", "gpt-4o-mini-tts")
VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "alloy")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY or not DISCORD_TOKEN:
    raise RuntimeError("OPENAI_API_KEY and DISCORD_TOKEN must be set in the environment or .env file.")

client_ai = OpenAI(api_key=OPENAI_API_KEY)
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

conversation_history = {}
listening_channels = {}
voice_clients = {}

def get_response(user_id: int, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": "You are a helpful and friendly AI assistant. Keep responses concise, fun, and natural."}
        ]
    
    conversation_history[user_id].append({"role": "user", "content": user_message})
    
    response = client_ai.chat.completions.create(
        model=CHAT_MODEL,
        messages=conversation_history[user_id],
        max_tokens=500
    )
    
    bot_response = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": bot_response})
    
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = [
            conversation_history[user_id][0]
        ] + conversation_history[user_id][-19:]
    
    return bot_response

def transcribe_audio(audio_path: str) -> str:
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client_ai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text.strip()
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return ""

def synthesize_to_file(text: str) -> Path:
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = Path(tmp_file.name)
    tmp_file.close()

    with client_ai.audio.speech.with_streaming_response.create(
        model=VOICE_MODEL,
        voice=VOICE_NAME,
        input=text,
    ) as response:
        response.stream_to_file(tmp_path)

    return tmp_path

async def speak_response(voice_client, text):
    try:
        if voice_client.is_playing():
            voice_client.stop()
        
        loop = asyncio.get_event_loop()
        audio_path = await loop.run_in_executor(None, synthesize_to_file, text)
        
        def cleanup(error):
            try:
                audio_path.unlink(missing_ok=True)
            except:
                pass

        source = discord.FFmpegPCMAudio(executable=FFMPEG_PATH, source=str(audio_path))
        voice_client.play(source, after=cleanup)
    except Exception as e:
        logging.error(f"Speak error: {e}")

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user}")

@bot.command(name="listen")
async def listen(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first!")
        return
    
    channel_id = ctx.author.voice.channel.id
    
    if listening_channels.get(channel_id, False):
        await ctx.send("Already listening!")
        return
    
    listening_channels[channel_id] = True
    
    voice_client = await ctx.author.voice.channel.connect()
    voice_clients[ctx.guild.id] = voice_client
    
    await ctx.send(f"👂 Listening! Say something and I'll respond with voice!")

@bot.command(name="unlisten")
async def unlisten(ctx):
    if ctx.voice_client and ctx.voice_client.is_connected():
        channel_id = ctx.voice_client.channel.id
        if channel_id in listening_channels:
            listening_channels[channel_id] = False
        await ctx.voice_client.disconnect()
        await ctx.send("Stopped listening 👋")

@bot.command(name="join")
async def join_voice(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first!")
        return
    
    await ctx.author.voice.channel.connect()
    await ctx.send("Joined ✅")

@bot.command(name="leave")
async def leave_voice(ctx):
    if ctx.voice_client and ctx.voice_client.is_connected():
        channel_id = ctx.voice_client.channel.id
        if channel_id in listening_channels:
            listening_channels[channel_id] = False
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected 👋")

@bot.command(name="chat")
async def chat(ctx, *, message: str):
    await ctx.send("Thinking... 🤔")
    try:
        response = get_response(ctx.author.id, message)
        await ctx.send(response)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command(name="talk")
async def talk(ctx, *, message: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first!")
        return
    
    await ctx.send("Thinking... 🤔")
    try:
        response = get_response(ctx.author.id, message)
        await ctx.send(f"💬 {response}")
        
        voice_client = ctx.voice_client
        if not voice_client or not voice_client.is_connected():
            voice_client = await ctx.author.voice.channel.connect()
        
        await speak_response(voice_client, response)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command(name="clear")
async def clear_history(ctx):
    if ctx.author.id in conversation_history:
        del conversation_history[ctx.author.id]
        await ctx.send("History cleared 🗑️")

@bot.command(name="speak")
async def speak(ctx, *, text: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first!")
        return

    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await ctx.author.voice.channel.connect()

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    await ctx.send("🎙️")
    await speak_response(ctx.voice_client, text)

@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Stopped ⏹️")

bot.run(DISCORD_TOKEN)
