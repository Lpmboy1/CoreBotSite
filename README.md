# Core Games Studio XP Dashboard

This repository contains a Flask web app and Discord sync bot for an XP-based progression system.

## Setup

1. Copy `.env.example` to `.env` and set your secrets:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_GUILD_ID`
   - `FLASK_SECRET_KEY`
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
   - `DISCORD_REDIRECT_URI`

2. Install dependencies:
   ```bash
   pip install flask requests discord.py
   ```

3. Run the web app:
   ```bash
   python3 web.py
   ```

4. Run the Discord bot:
   ```bash
   python3 main.py
   ```

## Notes

- `xp.db` is excluded from git.
- Use `http://localhost:5000` for the web frontend.
- Log in via Discord to sync XP with the database.
