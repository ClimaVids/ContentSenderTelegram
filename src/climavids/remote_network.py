from __future__ import annotations

import os
from typing import Any

import requests

# Public Cloudflare Worker endpoint for the Telegram Bot Interface.
# Keeping this as a code fallback prevents the publisher from silently
# losing the remote destination/force-run connection when a GitHub Actions
# repository variable is missing.
DEFAULT_BOT_API_URL = "https://climavids-content-sender-bot.birjand-climate.workers.dev"


def remote_base_url() -> str:
    configured = (os.getenv("CLIMAVIDS_BOT_API_URL") or "").strip().rstrip("/")
    return configured or DEFAULT_BOT_API_URL


def fetch_destinations(token: str) -> list[dict[str, Any]] | None:
    base = remote_base_url()
    try:
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
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"REMOTE_DESTINATIONS_ERROR {type(exc).__name__}: {exc}")
        return None


def fetch_force_run(token: str) -> dict[str, Any] | None:
    base = remote_base_url()
    try:
        response = requests.post(
            f"{base}/internal/force-run",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Cloudflare Bot Interface returned an invalid force-run payload")
        print(f"REMOTE_FORCE_RUN_OK pending={payload.get('pending')}")
        return payload
    except (requests.RequestException, ValueError) as exc:
        print(f"REMOTE_FORCE_RUN_ERROR {type(exc).__name__}: {exc}")
        return None
