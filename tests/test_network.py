from __future__ import annotations

from datetime import datetime

import pytest

from climavids.destinations import DEFAULT_TIMES, MAX_POSTS, _normalise_times, update_settings
from climavids.private_state import _fernet


def test_time_normalization() -> None:
    assert _normalise_times(["8:00", "20:00", "20:00"]) == ["08:00", "20:00"]
    assert _normalise_times(["bad"]) == DEFAULT_TIMES


def test_private_state_uses_bot_token_derived_encryption(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-one")
    encrypted_one = _fernet().encrypt(b'{"owner_chat_id":123}')
    assert _fernet().decrypt(encrypted_one) == b'{"owner_chat_id":123}'

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-two")
    with pytest.raises(Exception):
        _fernet().decrypt(encrypted_one)


def test_posts_limit_is_small_and_predictable() -> None:
    assert MAX_POSTS == 3
