from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


STATE_PATH = Path("data/private_state.enc")


def _fernet() -> Fernet:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    key = base64.urlsafe_b64encode(hashlib.sha256(token.encode("utf-8")).digest())
    return Fernet(key)


def _empty() -> dict[str, Any]:
    return {
        "owner_chat_id": None,
        "destinations": {},
        "delivery": {},
        "slot_content": {},
        "scheduled_reports": [],
        "update_offset": 0,
        "token_generation": "current",
    }


def load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _empty()
    try:
        encrypted = STATE_PATH.read_bytes()
        raw = _fernet().decrypt(encrypted)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("private state is not a JSON object")
        return data
    except InvalidToken:
        # The bot token was changed. The previous encrypted state cannot be
        # decrypted by design, so start a fresh private state and let the
        # current owner claim the bot again with /claim.
        return _empty()
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"private state is unreadable: {exc}") from exc


def save(data: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    encrypted = _fernet().encrypt(raw)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_bytes(encrypted)
    tmp.replace(STATE_PATH)


def ensure() -> dict[str, Any]:
    data = load()
    changed = False
    for key, default in _empty().items():
        if key not in data:
            data[key] = default
            changed = True
    if changed:
        save(data)
    return data
