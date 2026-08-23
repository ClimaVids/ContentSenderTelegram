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
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout = timeout
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")
        if not self.chat_id:
            raise TelegramError("TELEGRAM_CHAT_ID is not configured")
        if not self.chat_id.strip().lstrip("-").isdigit():
            raise TelegramError("TELEGRAM_CHAT_ID must be the numeric Telegram chat id")

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TelegramError(f"network error: {type(exc).__name__}") from exc

        if response.status_code == 429:
            try:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
            except (ValueError, TypeError, requests.exceptions.JSONDecodeError):
                retry_after = 5
            time.sleep(min(max(retry_after, 1), 60))
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                raise TelegramError(f"network error: {type(exc).__name__}") from exc

        if not response.ok:
            try:
                detail = response.json().get("description", "unknown telegram error")
            except (ValueError, requests.exceptions.JSONDecodeError):
                detail = response.text[:200] or "unknown telegram error"
            raise TelegramError(f"telegram status={response.status_code}: {detail}")

        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            raise TelegramError("telegram returned invalid JSON") from exc
        if not data.get("ok"):
            raise TelegramError(data.get("description", "telegram returned ok=false"))
        return data

    def check(self) -> dict[str, Any]:
        return self._request("getMe", {})

    def send_text(self, text: str, max_retries: int = 3) -> dict[str, Any]:
        payload = {"chat_id": int(self.chat_id), "text": text, "disable_web_page_preview": False}
        for attempt in range(max_retries):
            try:
                return self._request("sendMessage", payload)
            except TelegramError as exc:
                if attempt == max_retries - 1:
                    raise
                # Retry transient transport/5xx/rate-limit failures; keep the
                # backoff bounded so a long-lived scheduled job cannot stall.
                if "status=4" in str(exc) and "status=429" not in str(exc):
                    raise
                time.sleep(2 ** attempt)
        raise TelegramError("telegram publish failed after retries")
