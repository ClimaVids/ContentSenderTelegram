from datetime import datetime, timezone

import pytest

from climavids.content import render
from climavids.models import NewsItem
from climavids.publishers.telegram import TelegramError, TelegramPublisher


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


def test_render_does_not_duplicate_title_or_append_source_url() -> None:
    draft = render(
        make_item("خشکی چمن‌ها، خشکی تدبیر؛ در لندن محدودیت مصرف آب اعمال شده است."),
        style="news",
    )
    assert draft.body.count("خشکی چمن‌ها، خشکی تدبیر") == 1
    assert "https://example.com/source" not in draft.body
    assert "📌 منبع: groundwater-resources" in draft.body
    assert "🔗 ایمانی‌پور | @ClimaVids" in draft.body
    assert "🔗 https://t.me/climavid" in draft.body


def test_render_keeps_paragraphs_sentence_complete() -> None:
    long_summary = (
        "این یک پاراگراف خبری طولانی است که درباره وضعیت آب و خشکسالی توضیح می‌دهد. "
        "در ادامه نیز اطلاعات تکمیلی درباره بارش، مصرف آب و مدیریت منابع ارائه می‌شود. "
        "جمله سوم باید کامل بماند و در میانه عبارت بریده نشود."
    )
    draft = render(make_item(long_summary), style="news")
    paragraph = draft.body.split("\n\n")[1]
    assert not paragraph.endswith(("،", ",", ":", "؛", "-", "…"))


def test_telegram_publisher_rejects_non_numeric_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@ClimaVids")
    with pytest.raises(TelegramError, match="numeric Telegram chat id"):
        TelegramPublisher()
