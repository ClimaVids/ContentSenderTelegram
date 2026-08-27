# Content Sender Telegram

**ClimaVids Content Engine** is an autonomous, Telegram-first content pipeline for the Persian ClimaVids audience.

## Current status

The project is **live**. GitHub Actions checks the publication schedule every 15 minutes and publishes **at most one selected post per Tehran calendar day** during the daily window starting at 12:00 Asia/Tehran. Manual workflow runs can publish immediately for testing.

The pipeline:

1. Collects public Persian content from configured Telegram sources.
2. Deduplicates previously published items and near-duplicate stories.
3. Scores candidates using freshness, relevance, public need, credibility, engagement and uniqueness.
4. Generates a Persian ClimaVids-formatted post.
5. Publishes one selected post to the configured Telegram chat.
6. Persists publication state so the same day is not published twice.

## Sources

The default enabled sources are public Telegram channels configured in `data/sources.json`. Additional RSS/GDELT collectors remain available for future expansion.

## Configuration

Required GitHub repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

`TELEGRAM_CHAT_ID` must be the numeric ID of the destination channel/chat.

## Validation

CI runs tests, Python compilation and a non-publishing dry run. The live publisher has a dedicated scheduled workflow plus a manual workflow for controlled testing.
