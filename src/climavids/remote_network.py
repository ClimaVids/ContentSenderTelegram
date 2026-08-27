from __future__ import annotations

import os
from typing import Any

import requests


def remote_base_url() -> str:
    return (os.getenv("CLIMAVIDS_BOT_API_URL") or "").strip().rstrip("/")


def fetch_destinations(token: str) -> list[dict[str, Any]] | None:
    base = remote_base_url()
    if not base:
        return None
    response = requests.get(
        f"{base}/internal/destinations",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Cloudflare Bot Interface returned an invalid destinations payload")
    return [x for x in payload if isinstance(x, dict)]


def fetch_force_run(token: str) -> dict[str, Any] | None:
    base = remote_base_url()
    if not base:
        return None
    response = requests.post(
        f"{base}/internal/force-run",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None
