from __future__ import annotations

from datetime import datetime, timezone
import html
import re

import requests
from bs4 import BeautifulSoup

from climavids.models import NewsItem, Source
from climavids.utils import fingerprint

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ClimaVidsContentEngine/0.4; +https://github.com/ClimaVids/ContentSenderTelegram)"
}


def _publication_time(message, fallback: datetime) -> datetime:
    date_node = message.select_one("a.tgme_widget_message_date")
    if date_node:
        time_node = date_node.select_one("time[datetime]")
        if time_node:
            raw = time_node.get("datetime")
            if raw:
                try:
                    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if value.tzinfo is None:
                        value = value.replace(tzinfo=timezone.utc)
                    return value.astimezone(timezone.utc)
                except ValueError:
                    pass
    return fallback


def collect(source: Source, timeout: int = 20, limit: int = 30) -> list[NewsItem]:
    channel = str(source.channel or "").lstrip("@").strip()
    if not channel:
        raise ValueError(f"source {source.id} has no Telegram channel")

    response = requests.get(
        f"https://t.me/s/{channel}",
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    messages = soup.select("div.tgme_widget_message")
    fallback_time = datetime.now(timezone.utc)
    out: list[NewsItem] = []

    for message in messages[-limit:]:
        text_node = message.select_one("div.tgme_widget_message_text")
        if not text_node:
            continue

        text = html.unescape(text_node.get_text(" ", strip=True))
        if len(text) < 25:
            continue

        date_node = message.select_one("a.tgme_widget_message_date")
        link = date_node.get("href") if date_node else f"https://t.me/{channel}"
        title = re.sub(r"\s+", " ", text).strip()
        published_at = _publication_time(message, fallback_time)

        out.append(
            NewsItem(
                id=fingerprint(source.id, link or title),
                source_id=source.id,
                title=title[:500],
                url=link or f"https://t.me/{channel}",
                summary=title[:4000],
                published_at=published_at,
                category=source.categories[0] if source.categories else "general",
                trust_score=source.trust_score,
                country="IR",
                language=source.language,
            )
        )
    return out
