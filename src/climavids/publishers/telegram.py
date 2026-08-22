import os
import time
from typing import Any

import requests


class TelegramError(RuntimeError):
    pass


class TelegramPublisher:
    def __init__(self, token: str | None = None, chat_id: str = "@climavids", timeout: int = 20):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id
        self.timeout = timeout
        if not self.token:
            raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")

    def send_text(self, text: str, max_retries: int = 3) -> dict[str, Any]:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": False}
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt == max_retries - 1:
                    raise TelegramError(f"network error: {type(exc).__name__}") from exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 429:
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                time.sleep(min(int(retry_after), 60))
                continue
            if not response.ok:
                if attempt == max_retries - 1:
                    raise TelegramError(f"telegram status={response.status_code}")
                time.sleep(2 ** attempt)
                continue
            data = response.json()
            if not data.get("ok"):
                raise TelegramError("telegram returned ok=false")
            return data
        raise TelegramError("telegram publish failed after retries")
