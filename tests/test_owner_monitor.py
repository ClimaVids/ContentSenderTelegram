import climavids.owner as owner


def test_command_parser_accepts_bot_commands() -> None:
    assert owner._parse_command("/status") == ("/status", [])
    assert owner._parse_command("/help@somebot") == ("/help", [])
    assert owner._parse_command("/posts 2") == ("/posts", ["2"])


def test_command_parser_ignores_normal_text() -> None:
    assert owner._parse_command("سلام") == (None, [])


def test_owner_report_functions_exist_without_cross_dependency() -> None:
    assert callable(owner.build_report)
    assert callable(owner.build_network_report)
    assert callable(owner.build_logs)
    assert callable(owner.build_health)
    assert callable(owner.build_test)


def test_build_health_uses_telegram_api(monkeypatch) -> None:
    monkeypatch.setattr(
        owner,
        "telegram_call",
        lambda method, payload=None: {
            "getMe": {"ok": True, "result": {"id": 123, "username": "Climavid_bot"}},
            "getChat": {"ok": True, "result": {"id": -1001, "title": "Test", "type": "channel"}},
            "getChatMember": {"ok": True, "result": {"status": "administrator", "can_post_messages": True}},
        }[method],
    )
    monkeypatch.setattr(owner, "load_private", lambda: {"destinations": {"-1001": {"chat_id": -1001, "title": "Test", "type": "channel", "active": True}}})
    text = owner.build_health()
    assert "Bot API" in text
    assert "مقصدهای سالم: 1" in text
