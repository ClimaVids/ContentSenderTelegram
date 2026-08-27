from climavids.content import render
from climavids.models import NewsItem


def _item(summary: str = "بارش در چند منطقه افزایش یافته است. بررسی‌ها ادامه دارد.") -> NewsItem:
    return NewsItem(
        id="test-1",
        source_id="test-source",
        title="افزایش بارش در چند منطقه",
        url="https://example.com/news",
        summary=summary,
        category="weather",
        trust_score=80,
    )


def test_public_text_has_no_headline_or_source_identity() -> None:
    draft = render(_item())
    assert draft.title == ""
    assert "test-source" not in draft.body
    assert "https://example.com/news" not in draft.body
    assert not draft.body.startswith("افزایش بارش در چند منطقه")


def test_footer_is_present_and_not_cut() -> None:
    draft = render(_item("بارش در چند منطقه افزایش یافته است. " * 100))
    assert "📩 تبلیغات و همکاری: @Clima_Vids" in draft.body
    assert "🔗 ایمانی‌پور | @climavids" in draft.body
    assert draft.body.endswith("🔗 ایمانی‌پور | @climavids")
    assert len(draft.body) <= 3900


def test_body_does_not_end_with_partial_sentence() -> None:
    draft = render(_item("بارش در چند منطقه افزایش یافته است. این روند در برخی نقاط ادامه دارد"))
    assert draft.body.split("\n\n")[0].endswith((".", "!", "?", "؟", "؛"))
