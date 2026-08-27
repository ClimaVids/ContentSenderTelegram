from __future__ import annotations

import os
import re
from typing import Any

import requests

DEFAULT_MODEL = "gemini-3.5-flash-lite"
TERMINATORS = ".!?؟؛"


def _looks_complete(text: str) -> bool:
    text = re.sub(r"\s+", " ", text or "").strip()
    return bool(text) and text[-1] in TERMINATORS


def enhance_summary(summary: str, title: str, category: str) -> str:
    """Optionally rewrite a source summary using Gemini; reject visibly truncated AI output."""
    fallback = summary.strip()
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key or not fallback:
        return fallback

    model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
    prompt = (
        "متن زیر را برای انتشار در کانال فارسی ClimaVids بازنویسی کن. "
        "تیتر تولید نکن. نام منبع، نام کانال، شناسه کانال و لینک را حذف کن. "
        "عددها، تاریخ‌ها و واقعیت‌های اصلی را تغییر نده. "
        "لحن خبری، روشن و کوتاه باشد و از ادعاهای اضافه پرهیز کن. "
        "خروجی باید با یک جمله کامل و نشانه پایان جمله تمام شود. "
        "حداکثر 700 نویسه خروجی بده.\n\n"
        f"دسته: {category}\n"
        f"عنوان منبع: {title}\n"
        f"متن: {fallback}"
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        if not response.ok:
            return fallback
        data = response.json()
        candidate = (data.get("candidates") or [{}])[0]
        text = (
            candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            if isinstance(candidate, dict)
            else ""
        )
        finish_reason = str(candidate.get("finishReason", "STOP")) if isinstance(candidate, dict) else "STOP"
        text = str(text).strip()
        if finish_reason not in {"STOP", "MAX_TOKENS"}:
            return fallback
        # MAX_TOKENS is not accepted as a trustworthy rewrite unless the text
        # still visibly ends at a sentence boundary.
        if not _looks_complete(text):
            return fallback
        return text
    except (requests.RequestException, ValueError, TypeError, IndexError, AttributeError):
        return fallback
