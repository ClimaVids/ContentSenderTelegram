import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from climavids.models import NewsItem, Source


def _slug(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower()).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def parse_datetime(entry) -> datetime | None:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def collect_rss(source: Source, timeout: int = 20, max_items: int = 30) -> list[NewsItem]:
    feed = feedparser.parse(str(source.rss), request_headers={"User-Agent": "ClimaVidsContentEngine/0.1"})
    items: list[NewsItem] = []
    for entry in feed.entries[:max_items]:
        title = str(entry.get("title", "")).strip()
        url = str(entry.get("link", "")).strip()
        if not title or not url:
            continue
        summary = re.sub(r"\s+", " ", str(entry.get("summary", ""))).strip()
        item_id = _slug(source.id + "|" + url)
        items.append(
            NewsItem(
                id=item_id,
                source_id=source.id,
                title=title,
                url=url,
                summary=summary[:3000],
                published_at=parse_datetime(entry),
                category=source.category,
                trust_score=source.trust_score,
            )
        )
    return items
