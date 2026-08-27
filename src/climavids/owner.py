from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo("Asia/Tehran")
STATE_PATH = Path("data/state.json")
SCHEDULE_PATH = Path("data/schedule_state.json")
OWNER_STATE_PATH = Path("data/owner_state.json")

OWNER_HELP = """🔐 پنل خصوصی مالک ClimaVids

این پیام فقط برای مالک تأییدشده ربات ارسال می‌شود.

وظیفه سیستم:
• جمع‌آوری اخبار آب، هوا، اقلیم و محیط‌زیست از منابع فعال
• حذف موارد تکراری و امتیازدهی بر اساس تازگی، ارتباط، نیاز عمومی و اعتبار
• تولید متن فارسی مناسب کانال ClimaVids
• انتشار حداکثر یک محتوای منتخب در روز
• ثبت وضعیت انتشار و خطاها
• ارسال گزارش روزانه و هشدار خطا به مالک

دستورات مالک:
/status — وضعیت فعلی سیستم و آخرین انتشار
/report — گزارش کامل فعلی
/logs — خلاصه لاگ و آخرین خطاهای ثبت‌شده
/test — بررسی اتصال ربات و کانال مقصد بدون ارسال پست
/help — همین راهنما

نکته امنیتی: شناسه مالک از طریق TELEGRAM_OWNER_CHAT_ID کنترل می‌شود و هیچ کاربر دیگری نباید به این پنل دسترسی داشته باشد."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _config() -> tuple[str, str, str]:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    owner_id = (os.getenv("TELEGRAM_OWNER_CHAT_ID") or "").strip()
    target_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    if not owner_id or not owner_id.lstrip("-").isdigit():
        raise RuntimeError("TELEGRAM_OWNER_CHAT_ID must be a numeric Telegram chat id")
    if not target_id or not target_id.lstrip("-").isdigit():
        raise RuntimeError("TELEGRAM_CHAT_ID must be a numeric Telegram chat id")
    return token, owner_id, target_id


def telegram_call(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload or {},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram {method} failed"))
    return data


def send_owner(text: str) -> dict[str, Any]:
    token, owner_id, _ = _config()
    return telegram_call(token, "sendMessage", {"chat_id": int(owner_id), "text": text, "disable_web_page_preview": True})


def build_report() -> str:
    state = _load_json(STATE_PATH)
    schedule = _load_json(SCHEDULE_PATH)
    now = datetime.now(TZ)

    published = state.get("published", [])
    seen = state.get("seen", [])
    last_publication = schedule.get("last_publication")
    publication_dates = schedule.get("published_dates", [])

    last_line = "هیچ انتشار موفقی ثبت نشده است."
    if isinstance(last_publication, dict):
        last_line = (
            f"{last_publication.get('date', 'نامشخص')} | "
            f"{last_publication.get('at', 'نامشخص')}"
        )

    return (
        "📊 گزارش ClimaVids Content Engine\n\n"
        f"🕒 زمان گزارش: {now.strftime('%Y-%m-%d %H:%M:%S')} تهران\n"
        f"✅ تعداد انتشارهای ثبت‌شده: {len(published)}\n"
        f"👁 موارد دیده‌شده: {len(seen)}\n"
        f"📅 روزهای انتشار ثبت‌شده: {len(publication_dates)}\n"
        f"📤 آخرین انتشار: {last_line}\n\n"
        "🔎 وضعیت: موتور انتشار روزانه فعال است.\n"
        "⚠️ برای جزئیات خطاهای اجرایی، /logs را ارسال کنید."
    )


def build_logs_summary() -> str:
    state = _load_json(STATE_PATH)
    metrics = state.get("metrics", {})
    errors = metrics.get("errors", []) if isinstance(metrics, dict) else []
    lines = ["🧾 خلاصه لاگ ClimaVids", ""]
    if isinstance(metrics, dict):
        lines.extend([
            f"• آخرین اجرای ثبت‌شده: {metrics.get('last_run', 'نامشخص')}",
            f"• آخرین نتیجه: {metrics.get('last_result', 'نامشخص')}",
            f"• تعداد منابع خطادار: {metrics.get('last_source_errors', 0)}",
            f"• تعداد کاندیدها: {metrics.get('last_candidates', 0)}",
            f"• تعداد موارد انتخاب‌شده: {metrics.get('last_selected', 0)}",
        ])
    if errors:
        lines.append("\nآخرین خطاها:")
        for error in errors[-5:]:
            lines.append(f"• {error}")
    else:
        lines.append("\n✅ خطای ساختاری ثبت‌شده‌ای در state وجود ندارد.")
    return "\n".join(lines)


def build_test_report() -> str:
    token, owner_id, target_id = _config()
    me = telegram_call(token, "getMe").get("result", {})
    result = telegram_call(token, "getChat", {"chat_id": int(target_id)}).get("result", {})
    return (
        "🧪 تست سلامت ربات\n\n"
        f"🤖 ربات: @{me.get('username', 'unknown')}\n"
        f"🔐 مالک تأییدشده: {owner_id}\n"
        f"🎯 مقصد: {result.get('title') or result.get('username') or target_id}\n"
        f"📌 نوع مقصد: {result.get('type', 'unknown')}\n\n"
        "✅ اتصال Bot API و دسترسی به مقصد برقرار است.\n"
        "ℹ️ هیچ محتوایی در مقصد ارسال نشد."
    )


def command_for_update(update: dict[str, Any]) -> str | None:
    message = update.get("message") or {}
    text = str(message.get("text") or "").strip()
    return text.split()[0].split("@", 1)[0].lower() if text.startswith("/") else None


def poll_owner_commands() -> bool:
    token, owner_id, _ = _config()
    state = _load_json(OWNER_STATE_PATH)
    offset = int(state.get("update_offset", 0) or 0)
    response = telegram_call(token, "getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})
    updates = response.get("result", [])
    changed = False

    for update in updates:
        update_id = int(update.get("update_id", 0))
        state["update_offset"] = max(int(state.get("update_offset", 0) or 0), update_id + 1)
        changed = True

        message = update.get("message") or {}
        sender_chat_id = str((message.get("chat") or {}).get("id", "")).strip()
        if sender_chat_id != owner_id:
            continue

        command = command_for_update(update)
        if not command:
            continue

        try:
            if command == "/help":
                send_owner(OWNER_HELP)
            elif command == "/status":
                send_owner(build_report())
            elif command == "/report":
                send_owner(build_report())
            elif command == "/logs":
                send_owner(build_logs_summary())
            elif command == "/test":
                send_owner(build_test_report())
            else:
                send_owner("❓ دستور ناشناخته است. /help را ارسال کنید.")
        except Exception as exc:
            send_owner(f"🚨 خطا در اجرای دستور مالک\n\n{type(exc).__name__}: {exc}")

    if changed:
        _save_json(OWNER_STATE_PATH, state)
    return changed


def send_scheduled_report(report_type: str) -> None:
    state = _load_json(OWNER_STATE_PATH)
    now = datetime.now(TZ)
    key = f"{now:%Y-%m-%d}|{report_type}"
    sent_reports = state.get("sent_reports", [])
    if key in sent_reports:
        return
    title = "☀️ گزارش صبحگاهی ClimaVids" if report_type == "morning" else "🌙 گزارش شبانه ClimaVids"
    send_owner(f"{title}\n\n{build_report()}\n\nبرای جزئیات خطا: /logs")
    sent_reports.append(key)
    state["sent_reports"] = sent_reports[-180:]
    _save_json(OWNER_STATE_PATH, state)
