from __future__ import annotations

import os
import time
from typing import Any

import requests

from climavids.config import DESTINATION


class TelegramError(RuntimeError):
    pass


class TelegramPublisher:
    def __init__(self, token: str | None = None, chat_id: str = DESTINATION, timeout: int = 20):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or DESTINATION
        self.timeout = timeout
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")

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

    def destination_check(self) -> dict[str, Any]:
        return self._request("getChat", {"chat_id": self.chat_id})

    def bot_membership(self) -> dict[str, Any]:
        me = self.check().get("result", {})
        bot_id = me.get("id")
        if not bot_id:
            raise TelegramError("Telegram did not return bot id")
        return self._request("getChatMember", {"chat_id": self.chat_id, "user_id": bot_id})

    def send_text(self, text: str, max_retries: int = 3) -> dict[str, Any]:
        if not text.strip():
            raise TelegramError("cannot publish empty text")
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": False}
        for attempt in range(max_retries):
            try:
                return self._request("sendMessage", payload)
            except TelegramError as exc:
                if attempt == max_retries - 1:
                    raise
                if "status=4" in str(exc) and "status=429" not in str(exc):
                    raise
                time.sleep(2 ** attempt)
        raise TelegramError("telegram publish failed after retries")
