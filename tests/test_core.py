from datetime import datetime, timezone

from climavids.dedup import deduplicate
from climavids.models import NewsItem
from climavids.scoring import score


def item(i: str, title: str) -> NewsItem:
    return NewsItem(
        id=i,
        source_id="test",
        title=title,
        url=f"https://example.com/{i}",
        published_at=datetime.now(timezone.utc),
        trust_score=90,
    )


def test_deduplicate_merges_near_duplicates():
    items = [item("1", "بارش شدید در خراسان رضوی"), item("2", "بارش شدید در خراسان رضوی امروز")]
    assert len(deduplicate(items)) == 1


def test_water_story_scores_above_threshold():
    result = score(item("1", "هشدار سیلاب و بارش شدید در استان"))
    assert result.total >= 65
    assert result.status == "selected"
