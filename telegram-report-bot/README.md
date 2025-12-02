# Telegram Report Bot

This repo contains a ready-to-deploy Telegram bot that:
- Stores links and messages sent to it
- Exports daily Excel reports (Monday–Friday) at configured time
- Sends the report to the admin Telegram ID

Important: Do NOT put your bot token in the code. Set the following environment variables in your hosting platform:

```
BOT_TOKEN=<your-telegram-bot-token>
ADMIN_ID=1325034238
TIMEZONE=Asia/Kolkata
REPORT_HOUR=23
REPORT_MINUTE=0
```

Deploy on Railway:
1. Create a GitHub repository and push these files.
2. On Railway, choose "Deploy from GitHub" and connect the repository.
3. In Railway Project > Variables, add the environment variables listed above. Paste your token only in Railway variables (do not share it).
4. Railway will run the worker `python bot.py` and keep it online even if your PC is off.

Security:
- Revoke any token you posted publicly via @BotFather and generate a new one.
