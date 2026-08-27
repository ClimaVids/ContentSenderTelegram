import hashlib
import re

from climavids.models import NewsItem


def _norm(text: str) -> str:
    text = text.lower().replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\sآ-ی]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def signature(item: NewsItem) -> str:
    return hashlib.sha256(f"{item.url}|{_norm(item.title)}".encode()).hexdigest()[:24]


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if len(t) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def deduplicate(items: list[NewsItem], threshold: float = 0.62) -> list[NewsItem]:
    kept: list[NewsItem] = []
    seen_urls: set[str] = set()
    for item in items:
        canonical = str(item.url).split("#", 1)[0].rstrip("/")
        if canonical in seen_urls:
            continue
        if any(similarity(item.title, old.title) >= threshold for old in kept):
            continue
        seen_urls.add(canonical)
        kept.append(item)
    return kept
