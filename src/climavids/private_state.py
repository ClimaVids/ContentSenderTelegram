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


def load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"owner_chat_id": None, "destinations": {}, "delivery": {}, "slot_content": {}, "scheduled_reports": []}
    try:
        encrypted = STATE_PATH.read_bytes()
        raw = _fernet().decrypt(encrypted)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, InvalidToken, json.JSONDecodeError):
        raise RuntimeError("private state is unreadable or the bot token changed")


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
    for key, default in {
        "owner_chat_id": None,
        "destinations": {},
        "delivery": {},
        "slot_content": {},
        "scheduled_reports": [],
    }.items():
        if key not in data:
            data[key] = default
            changed = True
    if changed:
        save(data)
    return data
