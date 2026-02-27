import discord
from discord.ext import commands
import openai
import os

# Set up your OpenAI key
openai.api_key = 'YOUR_OPENAI_API_KEY'

# Set up the bot
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Join a voice channel
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You're not in a voice channel!")

# Leave a voice channel
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a voice channel!")

# Speak in voice channel
@bot.command()
async def speak(ctx, *, text):
    response = openai.Completion.create(
      engine="text-davinci-003",
      prompt=text,
      max_tokens=50
    )
    await ctx.send(response['choices'][0]['text'])

# Run the bot
bot.run('YOUR_DISCORD_BOT_TOKEN')
