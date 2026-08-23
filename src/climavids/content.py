from __future__ import annotations

from datetime import datetime, timezone
import os
import re

from climavids.models import ContentDraft, NewsItem

PERSIAN_STYLES = ["news", "short", "question", "analysis"]
DEFAULT_FOOTER = "🔗 ایمانی‌پور | @ClimaVids"
DEFAULT_CHANNEL_LINK = "🔗 https://t.me/climavid"
CTA_BY_STYLE = {
    "news": "👥 عضو کانال شو تا از تازه‌ترین خبرها جا نمونی!",
    "short": "💬 نظرتو درباره این موضوع بگو!",
    "question": "💬 نظرتو بگو؛ تجربه یا دیدگاهت برامون مهمه!",
    "analysis": "📢 برای تبلیغات و همکاری، پیام بده",
}
EMOJI_BY_STYLE = {
    "news": "📰",
    "short": "⚡",
    "question": "❓",
    "analysis": "💡",
}


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


def _headline(title: str, style: str) -> str:
    """Turn a source title into a compact, curiosity-oriented headline (<=10 words)."""
    clean = re.sub(r"\s+", " ", title).strip(" .؛:")
    words = clean.split()
    if len(words) > 10:
        clean = " ".join(words[:10]).rstrip("،,؛:.") + "…"
    if not clean:
        clean = "تازه‌ترین خبر در حوزه آب و اقلیم"
    prefix = {"news": "🔥", "short": "⚡", "question": "❓", "analysis": "💡"}.get(style, "🔥")
    return f"{prefix} {clean}"


def _paragraphs(item: NewsItem, label: str, clean_summary: str, style: str) -> list[str]:
    title = item.title.strip()
    if style == "question":
        return [
            f"📰 {clean_summary[:420] or title}",
            f"⚠️ این موضوع برای {label} چه معنایی دارد؟",
            "💬 تجربه یا نظر شما چیست؟",
        ]
    if style == "analysis":
        return [
            f"📰 {clean_summary[:380] or title}",
            f"📊 مقایسه: این رویداد چه تفاوتی با وضعیت معمول در {label} دارد؟",
            "💡 نتیجه: برای قضاوت دقیق‌تر، داده‌ها و منبع اصلی را هم باید در نظر گرفت.",
        ]
    if style == "short":
        return [
            f"⚡ {clean_summary[:420] or title}",
            f"💧 نکته مهم برای {label}: این خبر چه اثری بر مردم و تصمیم‌گیری‌ها دارد؟",
        ]
    return [
        f"📰 {clean_summary[:420] or title}",
        f"⚠️ اهمیت خبر: این رویداد به‌طور مستقیم با {label} مرتبط است.",
        "💡 برای برداشت دقیق‌تر، متن کامل خبر و منبع اصلی را بررسی کنید.",
    ]


def _hashtags(item: NewsItem, style: str) -> str:
    mapping = {
        "water": ["#آب", "#منابع_آب", "#مدیریت_آب"],
        "weather": ["#هواشناسی", "#آب_و_هوا", "#هشدار_هواشناسی"],
        "climate": ["#اقلیم", "#تغییر_اقلیم", "#خشکسالی"],
        "environment": ["#محیط_زیست", "#آب", "#اقلیم"],
        "agriculture": ["#کشاورزی", "#آب", "#منابع_آب"],
    }
    tags = mapping.get(item.category, ["#آب", "#اقلیم", "#هواشناسی"])
    return " ".join(tags[:3])


def _footer(item: NewsItem, style: str) -> str:
    sponsor_link = os.getenv("SPONSOR_LINK", "").strip()
    cta = CTA_BY_STYLE.get(style, CTA_BY_STYLE["news"])
    parts = [cta, DEFAULT_FOOTER, DEFAULT_CHANNEL_LINK]
    if sponsor_link:
        parts.append(f"🔗 اسپانسر: {sponsor_link}")
    return "\n\n" + "\n".join(parts)


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = item.title.strip()
    clean_summary = re.sub(r"<[^>]+>", " ", item.summary or "")
    clean_summary = re.sub(r"\s+", " ", clean_summary).strip()

    headline = _headline(title, style)
    body_parts = [headline]
    body_parts.extend(_paragraphs(item, label, clean_summary, style))
    body_parts.append(f"📌 منبع: {item.source_id}")
    body_parts.append(_hashtags(item, style))
    body_parts.append(_footer(item, style))

    body = "\n\n".join(body_parts)
    body = body[:3900]
    return ContentDraft(
        item_id=item.id,
        title=headline[:120],
        body=body,
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
