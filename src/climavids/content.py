from __future__ import annotations

from datetime import datetime, timezone
import re

from climavids.models import ContentDraft, NewsItem

PERSIAN_STYLES = ["news", "short", "question", "analysis"]
DEFAULT_FOOTER = "🔗 ایمانی‌پور | @ClimaVids"
DEFAULT_CHANNEL_LINK = "🔗 https://t.me/climavid"
AD_HANDLE = "@Clima_Vids"
CTA_BY_STYLE = {
    "news": "👥 عضو کانال شو تا از تازه‌ترین خبرها جا نمونی!\n📩 برای تبلیغات و همکاری: @Clima_Vids",
    "short": "💬 نظرتو درباره این موضوع بگو!\n📩 تبلیغات و همکاری: @Clima_Vids",
    "question": "💬 نظرتو بگو؛ تجربه یا دیدگاهت برامون مهمه!\n📩 تبلیغات و همکاری: @Clima_Vids",
    "analysis": "🧠 این تحلیل رو برای یک دوست بفرست.\n📩 برای تبلیغات و همکاری: @Clima_Vids",
}
EMOJI_BY_STYLE = {
    "news": "📰",
    "short": "⚡",
    "question": "❓",
    "analysis": "💡",
}

SENTENCE_RE = re.compile(r"(?<=[.!؟!?؛:])\s+")


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


def _normalize_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _remove_duplicate_title(summary: str, title: str) -> str:
    summary = summary.strip()
    title = title.strip(" .؛:")
    if not summary or not title:
        return summary
    if summary.casefold().startswith(title.casefold()):
        summary = summary[len(title):].lstrip(" ،,؛:.-")
    return summary


def _sentence_complete(text: str, max_chars: int) -> str:
    """Clip only at a sentence boundary whenever clipping is required."""
    text = _normalize_text(text)
    if len(text) <= max_chars:
        return text
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    kept: list[str] = []
    total = 0
    for sentence in sentences:
        extra = len(sentence) + (2 if kept else 0)
        if total + extra > max_chars:
            break
        kept.append(sentence)
        total += extra
    if kept:
        return "  ".join(kept).strip()
    # No sentence boundary exists; use a word boundary without inventing a
    # dangling sentence fragment.
    words = text.split()
    out: list[str] = []
    total = 0
    for word in words:
        extra = len(word) + (1 if out else 0)
        if total + extra > max_chars:
            break
        out.append(word)
        total += extra
    return " ".join(out).strip()


def _headline(title: str, style: str) -> str:
    clean = _normalize_text(title).strip(" .؛:")
    words = clean.split()
    if len(words) > 10:
        clean = " ".join(words[:10]).rstrip("،,؛:.") + "…"
    if not clean:
        clean = "تازه‌ترین خبر در حوزه آب و اقلیم"
    prefix = {"news": "🔥", "short": "⚡", "question": "❓", "analysis": "💡"}.get(style, "🔥")
    return f"{prefix} {clean}"


def _paragraphs(item: NewsItem, label: str, clean_summary: str, style: str) -> list[str]:
    title = _normalize_text(item.title)
    summary = _remove_duplicate_title(clean_summary, title)
    if not summary:
        summary = title

    if style == "question":
        return [
            f"📰 {_sentence_complete(summary, 520)}",
            f"🌍 این خبر چه اثری بر {label} و زندگی مردم می‌تواند داشته باشد؟",
            "💬 تجربه یا نظر شما چیست؟",
        ]
    if style == "analysis":
        return [
            f"📰 {_sentence_complete(summary, 500)}",
            f"📊 مقایسه: این رویداد چه تفاوتی با وضعیت معمول در {label} دارد؟",
            "🧠 نتیجه: تصمیم‌های درست باید با داده، اقلیم و شرایط محلی سازگار باشند.",
        ]
    if style == "short":
        return [
            f"⚡ {_sentence_complete(summary, 520)}",
            f"💧 نکته مهم برای {label}: این موضوع می‌تواند بر مردم و تصمیم‌گیری‌ها اثر بگذارد.",
        ]
    return [
        f"📰 {_sentence_complete(summary, 520)}",
        f"💧 چرا مهم است؟ چون مستقیماً با {label} و تصمیم‌های روزمره مردم ارتباط دارد.",
        "🧠 اصل مهم: مدیریت پایدار باید متناسب با اقلیم و منابع واقعی هر منطقه باشد.",
    ]


def _hashtags(item: NewsItem) -> str:
    mapping = {
        "water": ["#آب", "#منابع_آب", "#مدیریت_آب"],
        "weather": ["#هواشناسی", "#آب_و_هوا", "#هشدار_هواشناسی"],
        "climate": ["#اقلیم", "#تغییر_اقلیم", "#خشکسالی"],
        "environment": ["#محیط_زیست", "#آب", "#اقلیم"],
        "agriculture": ["#کشاورزی", "#آب", "#منابع_آب"],
    }
    return " ".join(mapping.get(item.category, ["#آب", "#اقلیم", "#هواشناسی"])[:3])


def _footer(style: str) -> str:
    cta = CTA_BY_STYLE.get(style, CTA_BY_STYLE["news"])
    return f"{cta}\n\n{DEFAULT_FOOTER}\n\n{DEFAULT_CHANNEL_LINK}"


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = _normalize_text(item.title)
    clean_summary = _normalize_text(item.summary or "")

    body_parts = [_headline(title, style)]
    body_parts.extend(_paragraphs(item, label, clean_summary, style))
    body_parts.append(f"📌 منبع: {item.source_id}")
    body_parts.append(_hashtags(item))
    body_parts.append(_footer(style))

    # Keep the complete output below Telegram's text limit while preserving
    # paragraph and sentence boundaries. This fallback is only defensive.
    body = "\n\n".join(body_parts)
    if len(body) > 3900:
        body_parts[1] = f"📰 {_sentence_complete(_remove_duplicate_title(clean_summary, title), 360)}"
        body = "\n\n".join(body_parts)
    body = body[:3900].rstrip()

    return ContentDraft(
        item_id=item.id,
        title=_headline(title, style)[:120],
        body=body,
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
