from __future__ import annotations

import os
from typing import Any

import requests

DEFAULT_MODEL = "gemini-3.5-flash-lite"


def enhance_summary(summary: str, title: str, category: str) -> str:
    """Optionally rewrite a source summary using Gemini; always falls back to input."""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key or not summary.strip():
        return summary.strip()

    model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
    prompt = (
        "متن زیر را برای انتشار در کانال فارسی ClimaVids بازنویسی کن. "
        "تیتر تولید نکن. نام منبع، نام کانال، شناسه کانال و لینک را حذف کن. "
        "عددها، تاریخ‌ها و واقعیت‌های اصلی را تغییر نده. "
        "لحن خبری، روشن و کوتاه باشد و از ادعاهای اضافه پرهیز کن. "
        "حداکثر 700 نویسه خروجی بده.\n\n"
        f"دسته: {category}\n"
        f"عنوان منبع: {title}\n"
        f"متن: {summary}"
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
            return summary.strip()
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return str(text).strip() or summary.strip()
    except (requests.RequestException, ValueError, TypeError, IndexError, AttributeError):
        return summary.strip()
