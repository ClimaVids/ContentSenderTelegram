# ClimaVids Telegram Content Engine

**Recommended repository name:** `climavids-telegram-content-engine`

This project is the automated content engine for the Persian **ClimaVids Telegram channel**. It is responsible for collecting relevant public stories, filtering and scoring them, turning them into Persian posts, publishing at most one selected post per Tehran calendar day, persisting state, and monitoring failures.

## How it works

1. GitHub Actions wakes the publisher every 15 minutes.
2. The scheduler checks the Tehran local publication window and prevents duplicate daily publication.
3. Enabled public Telegram sources are collected from `data/sources.json`.
4. Items are deduplicated and scored for freshness, relevance, public need, credibility, engagement and uniqueness.
5. The selected item is rendered as a clean Persian post. The public message does **not** include the original source name, external Telegram channel ID, or source link.
6. The post is sent to `TELEGRAM_CHAT_ID`.
7. Publication state and runtime diagnostics are persisted for future runs.
8. A separate owner-monitor workflow checks owner commands and sends morning/night reports.
9. Publication or monitoring failures trigger an immediate private alert to the owner when `TELEGRAM_OWNER_CHAT_ID` is configured.

## Owner-only Telegram panel

The bot has a private owner interface. Only the numeric chat ID stored in `TELEGRAM_OWNER_CHAT_ID` is authorized.

Commands:

- `/help` — private operating guide
- `/status` — current status and last publication
- `/report` — current report
- `/logs` — runtime diagnostics and recent errors
- `/test` — verify Bot API access and destination access without publishing a post

These commands are not exposed to normal users.

## Required GitHub repository secrets

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — numeric destination channel/chat ID
- `TELEGRAM_OWNER_CHAT_ID` — numeric private chat ID of the bot owner

## Workflows

- `publish.yml` — daily content selection and publication
- `owner-monitor.yml` — owner-only commands, scheduled reports and private monitoring alerts
- `manual-publish.yml` — controlled manual publication
- `live-smoke.yml` — live smoke checks
- `collector-smoke.yml` — collector checks
- `ci.yml` — tests, compilation and dry run

## Important security rule

Never place the bot token, owner chat ID or other secrets in source files, committed state, public posts or logs. The owner monitor deliberately avoids printing secret values.
