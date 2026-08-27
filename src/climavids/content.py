from __future__ import annotations

from datetime import datetime, timezone
import re

from climavids.ai import enhance_summary
from climavids.models import ContentDraft, NewsItem

PERSIAN_STYLES = ["news", "short", "question", "analysis"]
DEFAULT_FOOTER = "🔗 ایمانی‌پور | @climavids"
CTA_BY_STYLE = {
    "news": "👥 برای دریافت مطالب جدید، کانال ClimaVids را دنبال کنید!\n📩 تبلیغات و همکاری: @Clima_Vids",
    "short": "💬 نظرتان درباره این موضوع چیست؟\n📩 تبلیغات و همکاری: @Clima_Vids",
    "question": "💬 نظر و تجربه شما چیست؟\n📩 تبلیغات و همکاری: @Clima_Vids",
    "analysis": "🧠 این مطلب را برای یک دوست علاقه‌مند به آب و اقلیم بفرستید.\n📩 تبلیغات و همکاری: @Clima_Vids",
}

SENTENCE_RE = re.compile(r"(?<=[.!؟!?؛:])\s+")
TERMINATORS = ".!?؟؛"


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


def _complete_sentence(text: str, max_chars: int) -> str:
    """Return text ending at a sentence boundary; never cut a sentence mid-way."""
    text = _normalize_text(text)
    if not text:
        return ""

    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    if len(text) <= max_chars and text[-1] in TERMINATORS:
        return text

    kept: list[str] = []
    total = 0
    for sentence in sentences:
        extra = len(sentence) + (2 if kept else 0)
        if total + extra > max_chars:
            break
        kept.append(sentence)
        total += extra

    if kept:
        result = "  ".join(kept).strip()
        if result and result[-1] not in TERMINATORS:
            result += "。"
        return result

    # No sentence boundary was found. Use the full short text rather than
    # cutting it; add a Persian full stop only when it is absent.
    if len(text) <= max_chars:
        return text if text[-1] in TERMINATORS else text + "。"

    # Last resort: shorten at a word boundary and make the result explicit.
    words = text.split()
    out: list[str] = []
    total = 0
    for word in words:
        extra = len(word) + (1 if out else 0)
        if total + extra > max_chars:
            break
        out.append(word)
        total += extra
    result = " ".join(out).rstrip()
    if result and result[-1] not in TERMINATORS:
        result += "…"
    return result


def _paragraphs(item: NewsItem, label: str, clean_summary: str, style: str) -> list[str]:
    title = _normalize_text(item.title)
    summary = _remove_duplicate_title(clean_summary, title)
    if not summary:
        summary = title

    summary = _complete_sentence(summary, 650)

    if style == "question":
        return [
            summary,
            f"🌍 این خبر چه اثری بر {label} و زندگی مردم می‌تواند داشته باشد؟",
            "💬 تجربه یا نظر شما چیست؟",
        ]
    if style == "analysis":
        return [
            summary,
            f"📊 بررسی: این رویداد چه تفاوتی با وضعیت معمول در {label} دارد؟",
            "🧠 نتیجه: تصمیم‌های درست باید با داده، اقلیم و شرایط محلی سازگار باشند.",
        ]
    if style == "short":
        return [
            summary,
            f"💧 نکته مهم برای {label}: این موضوع می‌تواند بر مردم و تصمیم‌گیری‌ها اثر بگذارد.",
        ]
    return [
        summary,
        f"💧 چرا مهم است؟ چون با {label} و تصمیم‌های روزمره مردم ارتباط دارد.",
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
    return f"{cta}\n\n{DEFAULT_FOOTER}"


def _fit_body(core: list[str], footer: str, limit: int = 3900) -> str:
    """Fit content without ever truncating the footer or cutting a sentence."""
    fixed = "\n\n".join(footer.splitlines())
    # Keep footer complete and reserve space for it first.
    separator = "\n\n"
    reserve = len(fixed) + len(separator)
    available = max(400, limit - reserve)

    selected: list[str] = []
    used = 0
    for part in core:
        part = _normalize_text(part)
        if not part:
            continue
        if used + len(part) + (2 if selected else 0) > available:
            break
        selected.append(part)
        used += len(part) + (2 if selected else 0)

    if not selected and core:
        selected = [_complete_sentence(core[0], available)]

    body_core = "\n\n".join(selected).strip()
    return f"{body_core}{separator}{fixed}".strip()


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = _normalize_text(item.title)
    clean_summary = _normalize_text(item.summary or "")
    clean_summary = enhance_summary(clean_summary, title, item.category)

    # Public Telegram output intentionally contains no headline/title,
    # source identifier, source channel name, or source link.
    body_parts = _paragraphs(item, label, clean_summary, style)
    body_parts.append(_hashtags(item))
    footer = _footer(style)
    body = _fit_body(body_parts, footer, limit=3900)

    return ContentDraft(
        item_id=item.id,
        title="",
        body=body,
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
