from __future__ import annotations

from datetime import datetime, timezone
import html
import re

import requests
from bs4 import BeautifulSoup

from climavids.models import NewsItem, Source
from climavids.utils import fingerprint

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ClimaVidsContentEngine/0.3; +https://github.com/birjandclimate-arch/climavids-content-engine)"
}


def collect(source: Source, timeout: int = 20, limit: int = 30) -> list[NewsItem]:
    channel = str(source.channel or "").lstrip("@").strip()
    if not channel:
        raise ValueError(f"source {source.id} has no Telegram channel")

    response = requests.get(f"https://t.me/s/{channel}", headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    messages = soup.select("div.tgme_widget_message")
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
        out.append(
            NewsItem(
                id=fingerprint(source.id, link or title),
                source_id=source.id,
                title=title[:500],
                url=link or f"https://t.me/{channel}",
                summary=title[:4000],
                published_at=datetime.now(timezone.utc),
                category=source.categories[0] if source.categories else "general",
                trust_score=source.trust_score,
                country="IR",
                language=source.language,
            )
        )
    return out
