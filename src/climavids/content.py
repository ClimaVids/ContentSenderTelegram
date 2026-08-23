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


def _normalize(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _headline(title: str, style: str) -> str:
    """Create a compact headline of at most 10 whitespace-separated words."""
    clean = _normalize(title).strip(" .؛:")
    words = clean.split()
    if len(words) > 10:
        clean = " ".join(words[:10]).rstrip("،,؛:.") + "…"
    if not clean:
        clean = "تازه‌ترین خبر در حوزه آب و اقلیم"
    prefix = {"news": "🔥", "short": "⚡", "question": "❓", "analysis": "💡"}.get(style, "🔥")
    return f"{prefix} {clean}"


def _remove_duplicate_title(title: str, summary: str) -> str:
    """Remove a repeated title/headline prefix from the supplied summary."""
    clean_title = _normalize(title)
    clean_summary = _normalize(summary)
    if not clean_summary:
        return ""
    if clean_title and clean_summary.startswith(clean_title):
        remainder = clean_summary[len(clean_title):].lstrip(" :؛،-—–")
        if remainder:
            return remainder
        return ""
    # Also handle the common case where the summary starts with the headline plus
    # a punctuation mark or duplicated whitespace.
    escaped = re.escape(clean_title)
    if clean_title:
        pattern = rf"^{escaped}\s*[؛:،,\-—–.]\s*"
        remainder = re.sub(pattern, "", clean_summary, count=1).strip()
        if remainder != clean_summary:
            return remainder
    return clean_summary


def _complete_sentence(text: str, limit: int) -> str:
    """Trim only at a sentence boundary; never cut a sentence in half."""
    text = _normalize(text)
    if len(text) <= limit:
        return text
    candidate = text[:limit].rstrip()
    matches = list(re.finditer(r"[.!؟؛…](?:\s|$)", candidate))
    if matches:
        end = matches[-1].end()
        return candidate[:end].strip()
    # No punctuation before the limit: use a word boundary and close neutrally.
    words = candidate.rsplit(" ", 1)
    return words[0].strip() if len(words) == 2 else candidate


def _split_paragraphs(text: str, max_chars: int = 420) -> list[str]:
    """Build 2–3 compact paragraphs without cutting sentences."""
    text = _normalize(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!؟؛…])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    paragraphs: list[str] = []
    current = ""
    for sentence in sentences:
        trial = f"{current} {sentence}".strip() if current else sentence
        if current and len(trial) > max_chars:
            paragraphs.append(current)
            current = sentence
        else:
            current = trial
        if len(paragraphs) >= 3:
            break
    if current and len(paragraphs) < 3:
        paragraphs.append(current)
    return paragraphs[:3]


def _paragraphs(item: NewsItem, label: str, clean_summary: str, style: str) -> list[str]:
    title = _normalize(item.title)
    summary = _remove_duplicate_title(title, clean_summary)
    source_paragraphs = _split_paragraphs(summary)

    if style == "question":
        first = source_paragraphs[0] if source_paragraphs else title
        return [
            f"📰 {first}",
            f"🌍 این موضوع چه اثری بر {label} و زندگی روزمره مردم دارد؟",
            "💬 تجربه یا نظر شما چیست؟",
        ]

    if style == "analysis":
        first = source_paragraphs[0] if source_paragraphs else title
        second = source_paragraphs[1] if len(source_paragraphs) > 1 else ""
        result = [f"📰 {first}"]
        if second:
            result.append(f"📊 {second}")
        result.append(f"🧠 نتیجه: این موضوع نشان می‌دهد تصمیم‌های مرتبط با {label} باید بر پایه داده و مدیریت درست اتخاذ شوند.")
        return result

    if style == "short":
        first = source_paragraphs[0] if source_paragraphs else title
        return [
            f"⚡ {first}",
            f"💧 نکته مهم در حوزه {label}: این خبر چه پیامدی برای مردم و تصمیم‌گیری‌ها دارد؟",
        ]

    # News style: only facts/context from the source plus a neutral closing line.
    result = [f"📰 {p}" for p in source_paragraphs]
    if not result:
        result = [f"📰 {title}"]
    if len(result) < 3:
        result.append(f"🌍 این خبر با موضوع {label} ارتباط مستقیم دارد و باید در چارچوب شرایط محلی بررسی شود.")
    return result[:3]


def _hashtags(item: NewsItem) -> str:
    mapping = {
        "water": ["#آب", "#منابع_آب", "#مدیریت_آب"],
        "weather": ["#هواشناسی", "#آب_و_هوا", "#هشدار_هواشناسی"],
        "climate": ["#اقلیم", "#تغییر_اقلیم", "#خشکسالی"],
        "environment": ["#محیط_زیست", "#آب", "#اقلیم"],
        "agriculture": ["#کشاورزی", "#آب", "#منابع_آب"],
    }
    tags = mapping.get(item.category, ["#آب", "#اقلیم", "#هواشناسی"])
    return " ".join(tags[:3])


def _footer(style: str) -> str:
    sponsor_link = os.getenv("SPONSOR_LINK", "").strip()
    cta = CTA_BY_STYLE.get(style, CTA_BY_STYLE["news"])
    parts = [cta, DEFAULT_FOOTER, DEFAULT_CHANNEL_LINK]
    if sponsor_link:
        parts.append(f"🔗 اسپانسر: {sponsor_link}")
    return "\n\n" + "\n".join(parts)


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = _normalize(item.title)
    clean_summary = _normalize(item.summary)

    headline = _headline(title, style)
    body_parts = [headline]
    body_parts.extend(_paragraphs(item, label, clean_summary, style))
    # Keep source as text only; never expose the source URL at the end of the post.
    body_parts.append(f"📌 منبع: {item.source_id}")
    body_parts.append(_hashtags(item))
    body_parts.append(_footer(style))

    body = "\n\n".join(body_parts)
    if len(body) > 3900:
        # Reduce source-derived paragraphs first while preserving all footer elements.
        compact = []
        for part in body_parts:
            compact.append(part)
            if len("\n\n".join(compact)) > 3600:
                compact[-1] = _complete_sentence(part, 600)
                break
        body = "\n\n".join(compact + body_parts[len(compact):])
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
