from __future__ import annotations

import os
import time
from typing import Any

import requests


class TelegramError(RuntimeError):
    pass


class TelegramPublisher:
    def __init__(self, token: str | None = None, chat_id: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID") or "@climavids"
        self.timeout = timeout
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")
        if not self.chat_id:
            raise TelegramError("TELEGRAM_CHAT_ID is not configured")

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        response = requests.post(url, json=payload, timeout=self.timeout)
        if response.status_code == 429:
            retry_after = response.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(min(int(retry_after), 60))
            response = requests.post(url, json=payload, timeout=self.timeout)
        if not response.ok:
            raise TelegramError(f"telegram status={response.status_code}")
        data = response.json()
        if not data.get("ok"):
            raise TelegramError("telegram returned ok=false")
        return data

    def check(self) -> dict[str, Any]:
        return self._request("getMe", {})

    def send_text(self, text: str, max_retries: int = 3) -> dict[str, Any]:
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": False}
        for attempt in range(max_retries):
            try:
                return self._request("sendMessage", payload)
            except (requests.RequestException, TelegramError) as exc:
                if attempt == max_retries - 1:
                    if isinstance(exc, TelegramError):
                        raise
                    raise TelegramError(f"network error: {type(exc).__name__}") from exc
                time.sleep(2 ** attempt)
        raise TelegramError("telegram publish failed after retries")
