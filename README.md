# channel-guard-bot

Telegram bot that protects channel discussion groups from spam bots using emoji CAPTCHA verification.

## Features

- Emoji CAPTCHA for new members (pick the right emoji from a 2x3 grid)
- Auto-mute on join until CAPTCHA is solved
- Auto-kick after 60 second timeout
- Skips bots and admins
- Deletes messages from unverified users (safety net)
- `until_date` safety margin — if bot crashes, mute auto-expires

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Add the bot as **admin** to your channel's discussion group with permissions:
   - Delete messages
   - Restrict members
3. Copy `.env.example` to `.env` and set your `BOT_TOKEN`

## Run

```bash
# Direct
pip install -r requirements.txt
BOT_TOKEN=your-token python bot.py

# Docker
docker compose up -d
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
