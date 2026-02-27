# Discord Voice Bot

A lightweight Discord bot that joins your voice channel and speaks using OpenAI's TTS models.

## Prerequisites

- Python 3.12+
- `ffmpeg` available in your PATH
- Discord bot token (create at <https://discord.com/developers/applications>)
- OpenAI API key with access to the `gpt-4o-mini-tts` voice model

## Setup

```bash
# Clone the repo
 git clone git@github.com:sa7bioxix/discord-bot-voice.git
 cd discord-bot-voice

# Create and activate a virtual environment
 python3 -m venv venv
 source venv/bin/activate

# Install dependencies
 pip install -r requirements.txt
```

Create a `.env` file (or export environment variables however you prefer):

```
OPENAI_API_KEY=sk-...
DISCORD_TOKEN=...
OPENAI_VOICE_MODEL=gpt-4o-mini-tts   # optional override
OPENAI_VOICE_NAME=alloy              # optional override
FFMPEG_PATH=/usr/bin/ffmpeg          # optional override
```

## Usage

```bash
python bot.py
```

Once the bot is online in your server:

- `!join` – have the bot join your current voice channel
- `!leave` – disconnect from voice
- `!speak <text>` – synthesize the text and play it in the channel
- `!stop` – stop the current playback

Invite the bot to your server using the OAuth URL from the Discord Developer Portal (make sure you enable the **bot** scope and give it **Connect**, **Speak**, and **Send Messages** permissions).

## Notes

- Temporary audio files are created for each `!speak` command and cleaned up when playback finishes.
- If `ffmpeg` lives somewhere unusual, point `FFMPEG_PATH` to it.
- `.env`, virtualenvs, and generated audio files are ignored via `.gitignore`.
