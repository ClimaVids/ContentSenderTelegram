# Token-only architecture change

This release removes the need for destination and owner chat ID secrets.

- `TELEGRAM_BOT_TOKEN` is the only GitHub Actions Secret.
- Bot identity is discovered with Telegram `getMe`.
- Publication destination is fixed to `@climavids`.
- Owner claims a private control chat with `/claim`.
- The claimed owner chat ID is persisted in `data/owner_state.json`.
- Owner commands are private and handled by `owner-monitor.yml`.
