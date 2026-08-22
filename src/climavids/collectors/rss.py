from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time

import feedparser
import requests

from climavids.models import NewsItem, Source
from climavids.utils import fingerprint


HEADERS = {"User-Agent": "ClimaVidsContentEngine/0.2 (+https://github.com/birjandclimate-arch/climavids-content-engine)"}


def _published(entry) -> datetime | None:
    value = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def collect(source: Source, timeout: int = 15, limit: int = 50) -> list[NewsItem]:
    response = requests.get(str(source.endpoint or source.url), headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items: list[NewsItem] = []
    for entry in parsed.entries[:limit]:
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()
        if not title or not link:
            continue
        summary = (getattr(entry, "summary", "") or "").strip()
        items.append(
            NewsItem(
                id=fingerprint(title, link),
                source_id=source.id,
                title=title,
                url=link,
                summary=summary[:4000],
                published_at=_published(entry),
                category=source.categories[0] if source.categories else "general",
                trust_score=source.trust_score,
                language=source.language,
            )
        )
    time.sleep(0.05)
    return items
