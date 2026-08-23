from __future__ import annotations

from datetime import datetime, timezone
import os
import re

from climavids.models import ContentDraft, NewsItem

PERSIAN_STYLES = ["news", "short", "question", "analysis"]
DEFAULT_FOOTER = "ایمانی‌پور | @ClimaVids"
DEFAULT_CTA = "برای همکاری و تبلیغات پیام دهید"
DEFAULT_CHANNEL_LINK = "https://t.me/climavid"


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


def _footer() -> str:
    sponsor_link = os.getenv("SPONSOR_LINK", "").strip()
    parts = [DEFAULT_CTA, DEFAULT_FOOTER, f"🔗 {DEFAULT_CHANNEL_LINK}"]
    if sponsor_link:
        parts.append(f"لینک اسپانسر: {sponsor_link}")
    return "\n\n" + "\n".join(parts)


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
    body = (body + _footer())[:3900]
    return ContentDraft(
        item_id=item.id,
        title=title[:120],
        body=body,
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
