# ContentSenderTelegram

This project is the automated content engine for the Persian **ClimaVids Telegram channel**.

## Architecture

- Bot: `@Climavid_bot`
- Destination channel: `@climavids`
- Hosting/scheduler: GitHub Actions
- Required GitHub Secret: `TELEGRAM_BOT_TOKEN` only
- Publication frequency: at most one selected post per Tehran calendar day
- Owner control: private Telegram chat, claimed once with `/claim`

## Pipeline

1. GitHub Actions runs the publisher every 15 minutes.
2. The scheduler checks the Tehran daily publication window.
3. Public Telegram sources in `data/sources.json` are collected.
4. Duplicate and near-duplicate stories are filtered.
5. Remaining stories are scored for freshness, relevance, public need, credibility, engagement and uniqueness.
6. One selected story is converted into a Persian ClimaVids post.
7. The public post contains no original source name, external channel ID, source URL or separate headline.
8. The post is sent directly to `@climavids`.
9. Publication state and diagnostics are persisted in the repository.

## Private owner panel

The first owner who sends `/claim` to the bot in a private chat becomes the owner. The owner ID is stored in `data/owner_state.json`; no owner Secret is required.

Available owner commands:

- `/claim` — claim the private chat as the owner panel (one time)
- `/help` — complete operating guide
- `/status` — current status and last publication
- `/report` — detailed current report
- `/logs` — source counts, pipeline metrics and recent errors
- `/test` — verify Bot API, `@climavids` and bot membership/admin status without publishing

Normal users do not receive management output. They must not be able to see the owner panel.

## Scheduled owner reports

`owner-monitor.yml` checks private commands every 15 minutes and sends:

- morning report around 09:00 Tehran time
- night report around 21:00 Tehran time
- immediate private failure alerts when the publisher/monitor fails and an owner has been claimed

## Workflows

- `publish.yml` — scheduled publication
- `owner-monitor.yml` — owner commands and reports
- `manual-publish.yml` — manual publication to `@climavids`
- `live-smoke.yml` — optional live test message to `@climavids`
- `collector-smoke.yml` — collector test
- `ci.yml` — tests, compilation and dry run

## Setup

1. Add the token of `@Climavid_bot` as `TELEGRAM_BOT_TOKEN` in GitHub Actions Secrets.
2. Add `@Climavid_bot` to `@climavids` and make it an administrator with permission to post messages.
3. Open a private chat with `@Climavid_bot` and send `/claim`.
4. Send `/test` to verify the connection and destination.
5. Use `/status` or `/logs` for diagnostics.

Never put the bot token in source code, committed files, public posts or logs.
