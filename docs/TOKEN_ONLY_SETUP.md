# Token-only setup

Only `TELEGRAM_BOT_TOKEN` is required in GitHub Actions Secrets.

Bot: `@Climavid_bot`

Channel destination: `@climavids`

Owner setup: open a private chat with the bot and send `/claim`. The first private chat to claim becomes the owner and is persisted in `data/owner_state.json`.

Owner commands: `/help`, `/status`, `/report`, `/logs`, `/test`.
