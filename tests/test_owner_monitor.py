from climavids.owner import _parse_command


def test_command_parser_accepts_bot_commands() -> None:
    assert _parse_command("/status") == ("/status", [])
    assert _parse_command("/help@somebot") == ("/help", [])
    assert _parse_command("/posts 2") == ("/posts", ["2"])


def test_command_parser_ignores_normal_text() -> None:
    assert _parse_command("سلام") == (None, [])
