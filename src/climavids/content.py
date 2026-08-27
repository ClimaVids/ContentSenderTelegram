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

SENTENCE_RE = re.compile(r"(?<=[.!؟!?])\s+")
TERMINATORS = ".!?؟؛"
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
BARE_DOMAIN_RE = re.compile(r"(?<![@\w])(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[^\s]*)?")
HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{3,}")
HASHTAG_RE = re.compile(r"(?<!\w)#[\wآ-ی_]+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
SOURCE_PHRASE_RE = re.compile(r"(?:\s*[—–-]?\s*)?(?:مشروح\s+خبر|ادامه\s+خبر|جزئیات\s+بیشتر|منبع\s*:?)", re.IGNORECASE)


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


def _strip_source_artifacts(text: str) -> str:
    """Remove URLs, handles, source hashtags, markdown links and attribution fragments."""
    text = MARKDOWN_LINK_RE.sub(" ", text or "")
    text = URL_RE.sub(" ", text)
    text = BARE_DOMAIN_RE.sub(" ", text)
    text = HANDLE_RE.sub(" ", text)
    text = HASHTAG_RE.sub(" ", text)
    text = SOURCE_PHRASE_RE.sub(" ", text)
    text = re.sub(r"\s+[|•·]+\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t,،؛:|-–—")


def _remove_duplicate_title(summary: str, title: str) -> str:
    summary = summary.strip()
    title = title.strip(" .؛:")
    if not summary or not title:
        return summary
    if summary.casefold().startswith(title.casefold()):
        summary = summary[len(title):].lstrip(" ،,؛:.-")
    return summary


def _repair_leading_fragment(text: str) -> str:
    """Repair known feed truncation artifacts without inventing facts."""
    text = text.strip()
    replacements = {
        "ار گلستان": "در گلستان",
        "ر گلستان": "در گلستان",
    }
    for old, new in replacements.items():
        if text.startswith(old):
            return new + text[len(old):]
    return text


def _complete_sentence(text: str, max_chars: int) -> str:
    """Keep complete sentences and never silently cut the public copy."""
    text = _normalize_text(text)
    if not text:
        return ""
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    if len(text) <= max_chars:
        return text if text[-1] in TERMINATORS else text + "。"

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
        return result if result[-1] in TERMINATORS else result + "。"
    return ""


def _paragraphs(item: NewsItem, label: str, clean_summary: str, style: str) -> list[str]:
    title = _normalize_text(item.title)
    summary = _repair_leading_fragment(_remove_duplicate_title(_strip_source_artifacts(clean_summary), title))
    if not summary:
        summary = _repair_leading_fragment(_strip_source_artifacts(title))
    summary = _complete_sentence(summary, 650)

    if style == "question":
        return [summary, f"🌍 این خبر چه اثری بر {label} و زندگی مردم می‌تواند داشته باشد؟", "💬 تجربه یا نظر شما چیست؟"]
    if style == "analysis":
        return [summary, f"📊 بررسی: این رویداد چه تفاوتی با وضعیت معمول در {label} دارد؟", "🧠 نتیجه: تصمیم‌های درست باید با داده، اقلیم و شرایط محلی سازگار باشند."]
    if style == "short":
        return [summary, f"💧 نکته مهم برای {label}: این موضوع می‌تواند بر مردم و تصمیم‌گیری‌ها اثر بگذارد."]
    return [summary, f"💧 چرا مهم است؟ چون با {label} و تصمیم‌های روزمره مردم ارتباط دارد.", "🧠 اصل مهم: مدیریت پایدار باید متناسب با اقلیم و منابع واقعی هر منطقه باشد."]


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
    fixed_footer = footer.strip()
    available = max(400, limit - len(fixed_footer) - 2)
    selected: list[str] = []
    used = 0
    for part in core:
        part = _normalize_text(part)
        if not part:
            continue
        extra = len(part) + (2 if selected else 0)
        if used + extra > available:
            break
        selected.append(part)
        used += extra
    if not selected and core and available > 0:
        first = _complete_sentence(core[0], available)
        if first:
            selected = [first]
    return f"{'\\n\\n'.join(selected).strip()}\n\n{fixed_footer}".strip()


def render(item: NewsItem, style: str = "news") -> ContentDraft:
    label = category_label(item.category)
    title = _normalize_text(item.title)
    clean_summary = _normalize_text(item.summary or "")
    clean_summary = enhance_summary(clean_summary, title, item.category)
    clean_summary = _strip_source_artifacts(clean_summary)

    body_parts = _paragraphs(item, label, clean_summary, style)
    body_parts.append(_hashtags(item))
    footer = _footer(style)
    body = _fit_body(body_parts, footer, limit=3900)

    # Final public-output sanitization. Only the fixed ClimaVids footer may contain our handles.
    core, _, fixed = body.rpartition("\n\n")
    core = _strip_source_artifacts(core)
    body = f"{core}\n\n{fixed}".strip()
    body = body.replace("📩 تبلیغات و همکاری: Clima_Vids", "📩 تبلیغات و همکاری: @Clima_Vids")
    body = body.replace("🔗 ایمانی‌پور | climavids", "🔗 ایمانی‌پور | @climavids")

    if len(body) > 3900:
        body = _fit_body([core], footer, limit=3900)
        body = body.replace("📩 تبلیغات و همکاری: Clima_Vids", "📩 تبلیغات و همکاری: @Clima_Vids")
        body = body.replace("🔗 ایمانی‌پور | climavids", "🔗 ایمانی‌پور | @climavids")

    return ContentDraft(
        item_id=item.id,
        title="",
        body=body,
        style=style,
        with_image=False,
        source_url=item.url,
        created_at=datetime.now(timezone.utc),
    )
