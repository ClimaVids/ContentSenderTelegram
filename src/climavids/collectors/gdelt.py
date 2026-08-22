from __future__ import annotations

from datetime import datetime, timezone
import requests

from climavids.models import NewsItem, Source
from climavids.utils import fingerprint


HEADERS = {"User-Agent": "ClimaVidsContentEngine/0.2"}


def collect(source: Source, timeout: int = 20, limit: int = 50) -> list[NewsItem]:
    endpoint = str(source.endpoint or source.url)
    data = requests.get(endpoint, headers=HEADERS, timeout=timeout).json()
    rows = data.get("articles", [])
    out: list[NewsItem] = []
    for row in rows[:limit]:
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        if not title or not url:
            continue
        date_text = row.get("seendate") or ""
        published = None
        if len(date_text) >= 14:
            try:
                published = datetime.strptime(date_text[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        out.append(
            NewsItem(
                id=fingerprint(title, url),
                source_id=source.id,
                title=title,
                url=url,
                summary=(row.get("domain") or "").strip(),
                published_at=published,
                category=source.categories[0] if source.categories else "general",
                trust_score=source.trust_score,
                country="IR" if "iran" in endpoint.lower() else "GLOBAL",
                language=source.language,
            )
        )
    return out
