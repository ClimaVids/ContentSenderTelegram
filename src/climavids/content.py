from __future__ import annotations

from datetime import datetime, timezone
import re

from climavids.models import ContentDraft, NewsItem

PERSIAN_STYLES = ["news", "short", "question", "analysis"]


def category_label(category: str) -> str:
    return {
        "water": "آب و منابع آب",
        "weather": "هواشناسی",
        "climate": "اقلیم و تغییر اقلیم",
        "environment": "محیط‌زیست",
        "agriculture": "کشاورزی و آب",
    }.get(category, "اخبار مرتبط")


def choose_style(item: NewsItem, index: int = 0) -> str:
    return PERSIAN_STYLES[index % len(PERSIAN_STYLES)]


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = item.title.strip()
    clean_summary = re.sub(r"<[^>]+>", " ", item.summary or "").strip()
    if style == "short":
        body = f"🟦 {title}\n\nمنبع: {item.source_id}"
    elif style == "question":
        body = f"❓ {title}\n\nبه نظر شما این رویداد چه اثری بر {label} دارد؟\n\nمنبع: {item.source_id}"
    elif style == "analysis":
        body = f"📊 {label}\n\n{title}\n\n{clean_summary[:700]}\n\nنکته: برای تفسیر دقیق‌تر، داده‌ها و منبع اصلی را نیز بررسی کنید.\n\nمنبع: {item.source_id}"
    else:
        body = f"📰 {title}\n\n{clean_summary[:900]}\n\nمنبع: {item.source_id}"
    return ContentDraft(
        item_id=item.id,
        title=title[:120],
        body=body[:3900],
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
