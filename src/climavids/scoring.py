from datetime import datetime, timezone

from climavids.models import NewsItem, ScoredItem

KEYWORDS = {
    "آب": 1.0, "منابع آب": 1.2, "خشکسالی": 1.2, "سیلاب": 1.25,
    "بارش": 1.15, "هواشناسی": 1.15, "اقلیم": 1.2, "تغییر اقلیم": 1.3,
    "گرما": 1.0, "موج گرما": 1.2, "یخبندان": 1.0, "گردوغبار": 0.95,
    "سد": 1.0, "رودخانه": 0.95, "کشاورزی": 0.75, "محیط زیست": 0.8,
}


def _freshness(item: NewsItem) -> float:
    if not item.published_at:
        return 50.0
    age_hours = max((datetime.now(timezone.utc) - item.published_at).total_seconds() / 3600, 0)
    return max(0.0, min(100.0, 100.0 * (0.5 ** (age_hours / 36.0))))


def _relevance(item: NewsItem) -> float:
    text = f"{item.title} {item.summary}".lower()
    weights = [w for k, w in KEYWORDS.items() if k in text]
    if not weights:
        return 25.0
    return min(100.0, 35.0 + 35.0 * max(weights) + 8.0 * (len(weights) - 1))


def score(item: NewsItem, uniqueness: float = 80.0) -> ScoredItem:
    relevance = _relevance(item)
    public_need = min(100.0, relevance * 0.75 + 15.0)
    engagement = min(100.0, relevance * 0.70 + (10.0 if any(x in item.title for x in ("چرا", "چگونه", "هشدار", "فوری")) else 0.0))
    result = ScoredItem(
        item=item,
        freshness=_freshness(item),
        relevance=relevance,
        public_need=public_need,
        credibility=float(item.trust_score),
        engagement=engagement,
        uniqueness=uniqueness,
    )
    result.status = "selected" if result.total >= 65 else "rejected"
    return result
