from climavids.owner import command_for_update


def test_command_parser_accepts_bot_commands() -> None:
    assert command_for_update({"message": {"text": "/status"}}) == "/status"
    assert command_for_update({"message": {"text": "/help@somebot"}}) == "/help"


def test_command_parser_ignores_normal_text() -> None:
    assert command_for_update({"message": {"text": "سلام"}}) is None
