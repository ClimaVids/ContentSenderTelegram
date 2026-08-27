from datetime import datetime, timezone

from climavids.content import render
from climavids.models import NewsItem
from climavids.publishers.telegram import TelegramPublisher


def make_item(summary: str) -> NewsItem:
    return NewsItem(
        id="fmt-1",
        source_id="groundwater-resources",
        title="خشکی چمن‌ها، خشکی تدبیر",
        summary=summary,
        url="https://example.com/source",
        published_at=datetime.now(timezone.utc),
        trust_score=90,
        category="water",
    )


def test_render_hides_title_source_and_external_channel_details() -> None:
    draft = render(
        make_item(
            "خشکی چمن‌ها، خشکی تدبیر؛ در لندن محدودیت مصرف آب اعمال شده است. "
            "[مشروح خبر](https://news.example/test) @niroonline"
        ),
        style="news",
    )
    assert draft.title == ""
    assert "خشکی چمن‌ها، خشکی تدبیر" not in draft.body
    assert "https://example.com/source" not in draft.body
    assert "groundwater-resources" not in draft.body
    assert "news.example" not in draft.body
    assert "@niroonline" not in draft.body
    assert "@Clima_Vids" in draft.body
    assert "@climavids" in draft.body


def test_render_repairs_known_feed_fragment_and_preserves_complete_sentences() -> None:
    draft = render(
        make_item(
            "ار گلستان، نمایندگان گرگان و آق‌قلا در مجلس شورای اسلامی و جمعی از مدیران محلی "
            "در شهرستان آق‌قلا به بهره‌برداری رسید."
        ),
        style="news",
    )
    assert draft.body.startswith("در گلستان،")
    assert not draft.body.endswith(("،", ",", ":", "؛", "-", "…"))
    assert "@Clima_Vids" in draft.body
    assert "🔗 ایمانی‌پور | @climavids" in draft.body


def test_render_keeps_paragraphs_sentence_complete() -> None:
    long_summary = (
        "این یک پاراگراف خبری طولانی است که درباره وضعیت آب و خشکسالی توضیح می‌دهد. "
        "در ادامه نیز اطلاعات تکمیلی درباره بارش، مصرف آب و مدیریت منابع ارائه می‌شود. "
        "جمله سوم باید کامل بماند و در میانه عبارت بریده نشود."
    )
    draft = render(make_item(long_summary), style="news")
    assert draft.body
    assert not draft.body.endswith(("،", ",", ":", "؛", "-", "…"))


def test_telegram_publisher_defaults_to_climavids(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    publisher = TelegramPublisher()
    assert publisher.chat_id == "@climavids"
