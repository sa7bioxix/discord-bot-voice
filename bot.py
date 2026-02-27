import asyncio
import logging
import os
import tempfile
from pathlib import Path

import discord
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

if not OPENAI_API_KEY or not DISCORD_TOKEN:
    raise RuntimeError("OPENAI_API_KEY and DISCORD_TOKEN must be set in the environment or .env file.")

client_ai = OpenAI(api_key=OPENAI_API_KEY)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def synthesize_to_file(text: str) -> Path:
    """Generate TTS audio for the given text using OpenAI and return the path."""
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

async def ensure_voice_client(ctx: commands.Context) -> discord.VoiceClient:
    if ctx.voice_client and ctx.voice_client.is_connected():
        return ctx.voice_client

    if not ctx.author.voice or not ctx.author.voice.channel:
        raise commands.CommandError("You're not connected to a voice channel. Join one and try again or use !join.")

    return await ctx.author.voice.channel.connect()

@bot.event
async def on_ready():
    logging.info("Logged in as %s", bot.user)

@bot.command(name="join")
async def join_voice(ctx: commands.Context):
    try:
        await ensure_voice_client(ctx)
        await ctx.send("Joined your voice channel ✅")
    except commands.CommandError as error:
        await ctx.send(str(error))

@bot.command(name="leave")
async def leave_voice(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel 👋")
    else:
        await ctx.send("I'm not in a voice channel.")

@bot.command(name="speak")
async def speak(ctx: commands.Context, *, text: str):
    if not text:
        await ctx.send("Give me something to say, e.g. `!speak Hello Chef Issam!`")
        return

    voice_client = await ensure_voice_client(ctx)

    if voice_client.is_playing():
        voice_client.stop()

    await ctx.send("Cooking up that voice line… 🎙️")
    loop = asyncio.get_running_loop()
    audio_path = await loop.run_in_executor(None, synthesize_to_file, text)

    def cleanup(error: Exception | None):
        try:
            audio_path.unlink(missing_ok=True)
        except Exception:
            logging.exception("Failed to delete temp audio file %s", audio_path)

        if error:
            logging.error("Playback error: %s", error)

    source = discord.FFmpegPCMAudio(
        executable=FFMPEG_PATH,
        source=str(audio_path),
    )
    voice_client.play(source, after=cleanup)

@bot.command(name="stop")
async def stop(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Stopped playback ⏹️")
    else:
        await ctx.send("Nothing is playing right now.")

bot.run(DISCORD_TOKEN)
