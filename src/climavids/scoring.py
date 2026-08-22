from __future__ import annotations

from datetime import datetime, timezone

from climavids.models import NewsItem, ScoredItem

KEYWORDS = {
    "water": ["آب", "سد", "رودخانه", "آبخوان", "خشکسالی", "منابع آب", "بارش"],
    "weather": ["هواشناسی", "باران", "برف", "توفان", "گرما", "سرما", "سیلاب", "گردوخاک"],
    "climate": ["اقلیم", "تغییر اقلیم", "گرمایش", "خشکسالی", "انتشار کربن", "آب‌وهوا"],
    "environment": ["محیط زیست", "آلودگی", "ریزگرد", "تالاب", "جنگل"],
    "agriculture": ["کشاورزی", "زراعت", "آبیاری", "کشت", "محصول"],
}


def relevance(title: str, category: str) -> float:
    t = title.lower()
    words = KEYWORDS.get(category, []) + ["آب", "هواشناسی", "اقلیم", "سیلاب", "خشکسالی", "بارش"]
    hits = sum(1 for word in words if word in t)
    return min(100.0, 45.0 + min(55, hits * 12))


def public_need(title: str) -> float:
    urgent = ["هشدار", "سیلاب", "موج گرما", "سرمای شدید", "آلودگی", "کمبود آب", "خشکسالی"]
    return min(100.0, 55.0 + sum(1 for word in urgent if word in title) * 15.0)


def freshness(published_at) -> float:
    if not published_at:
        return 45.0
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600)
    return max(5.0, 100.0 - age_hours * 4.0)


def score(item: NewsItem) -> ScoredItem:
    result = ScoredItem(
        item=item,
        freshness=freshness(item.published_at),
        relevance=relevance(item.title, item.category),
        public_need=public_need(item.title),
        credibility=float(item.trust_score),
        engagement=min(100.0, 45.0 + (15.0 if "؟" in item.title else 0.0) + (20.0 if any(x in item.title for x in ["هشدار", "بحران", "بی‌سابقه"]) else 0.0)),
        uniqueness=70.0,
    )
    result.status = "selected" if result.total >= 65 else "rejected"
    return result
