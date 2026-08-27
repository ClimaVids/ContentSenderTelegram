from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from climavids.config import DESTINATION

TZ = ZoneInfo("Asia/Tehran")
STATE_PATH = Path("data/state.json")
SCHEDULE_PATH = Path("data/schedule_state.json")
OWNER_STATE_PATH = Path("data/owner_state.json")

OWNER_HELP = """🔐 پنل خصوصی مالک ClimaVids

وظیفه ربات:
• جمع‌آوری اخبار آب، هوا، اقلیم و محیط‌زیست
• حذف مطالب تکراری
• امتیازدهی و انتخاب محتوای مناسب
• تولید متن فارسی برای کانال ClimaVids
• انتشار حداکثر یک مطلب در روز
• ثبت لاگ و وضعیت اجرا
• گزارش‌دهی و هشدار خطا برای مالک

دستورات مالک:
/claim — ثبت این گفت‌وگوی خصوصی به‌عنوان پنل مالک؛ فقط یک‌بار
/status — وضعیت کلی موتور و آخرین انتشار
/report — گزارش کامل
/logs — جزئیات آخرین اجرا، منابع و خطاها
/test — تست Bot API، مقصد و سطح دسترسی، بدون ارسال پست
/help — نمایش همین راهنما

مقصد انتشار: @climavids

پس از ثبت مالک، هیچ کاربر دیگری نمی‌تواند به این فرمان‌ها دسترسی داشته باشد."""


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


def _config() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    return token


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


def send_owner(chat_id: str | int, text: str) -> dict[str, Any]:
    return telegram_call(_config(), "sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def build_report() -> str:
    state = _load_json(STATE_PATH)
    schedule = _load_json(SCHEDULE_PATH)
    now = datetime.now(TZ)
    published = state.get("published", [])
    seen = state.get("seen", [])
    last_publication = schedule.get("last_publication")
    publication_dates = schedule.get("published_dates", [])
    metrics = state.get("metrics", {}) if isinstance(state.get("metrics", {}), dict) else {}

    last_line = "هیچ انتشار موفقی ثبت نشده است."
    if isinstance(last_publication, dict):
        last_line = f"{last_publication.get('date', 'نامشخص')} | {last_publication.get('at', 'نامشخص')}"

    owner = _load_json(OWNER_STATE_PATH)
    owner_id = owner.get("owner_chat_id", "ثبت نشده")

    return (
        "📊 گزارش ClimaVids ContentSenderTelegram\n\n"
        f"🕒 زمان: {now.strftime('%Y-%m-%d %H:%M:%S')} تهران\n"
        f"🤖 ربات: {owner.get('bot_username', 'در اجرای بعدی شناسایی می‌شود')}\n"
        f"🔐 مالک: {owner_id}\n"
        f"🎯 مقصد انتشار: {DESTINATION}\n"
        f"✅ انتشارهای ثبت‌شده: {len(published)}\n"
        f"👁 موارد دیده‌شده: {len(seen)}\n"
        f"📅 روزهای انتشار: {len(publication_dates)}\n"
        f"📤 آخرین انتشار: {last_line}\n"
        f"📥 آیتم خام آخرین اجرا: {metrics.get('last_raw_items', 'نامشخص')}\n"
        f"🎯 کاندیدهای آخرین اجرا: {metrics.get('last_candidates', 'نامشخص')}\n"
        f"⚠️ خطاهای منابع آخرین اجرا: {metrics.get('last_source_errors', 'نامشخص')}\n"
    )


def build_logs_summary() -> str:
    state = _load_json(STATE_PATH)
    metrics = state.get("metrics", {})
    errors = metrics.get("errors", []) if isinstance(metrics, dict) else []
    lines = ["🧾 لاگ ClimaVids ContentSenderTelegram", ""]
    if isinstance(metrics, dict):
        source_counts = metrics.get("last_source_counts", {})
        lines.extend([
            f"• آخرین اجرا: {metrics.get('last_run', 'نامشخص')}",
            f"• نتیجه: {metrics.get('last_result', 'نامشخص')}",
            f"• منابع فعال: {metrics.get('last_sources', 'نامشخص')}",
            f"• آیتم خام: {metrics.get('last_raw_items', 'نامشخص')}",
            f"• آیتم یکتا: {metrics.get('last_unique_items', 'نامشخص')}",
            f"• کاندیدها: {metrics.get('last_candidates', 'نامشخص')}",
            f"• انتخاب‌شده: {metrics.get('last_selected', 'نامشخص')}",
            f"• خطای منابع: {metrics.get('last_source_errors', 0)}",
        ])
        if source_counts:
            lines.append("• خروجی هر منبع: " + ", ".join(f"{k}={v}" for k, v in source_counts.items()))
    if errors:
        lines.append("\nآخرین خطاها:")
        lines.extend(f"• {error}" for error in errors[-5:])
    else:
        lines.append("\n✅ خطای ثبت‌شده‌ای در state وجود ندارد.")
    return "\n".join(lines)


def build_test_report() -> str:
    token = _config()
    me = telegram_call(token, "getMe").get("result", {})
    result = telegram_call(token, "getChat", {"chat_id": DESTINATION}).get("result", {})
    bot_id = me.get("id")
    membership = telegram_call(token, "getChatMember", {"chat_id": DESTINATION, "user_id": bot_id}).get("result", {})
    status = membership.get("status", "unknown")

    recommendations: list[str] = []
    if status in {"left", "kicked"}:
        recommendations.append("ربات عضو کانال مقصد نیست.")
    elif status not in {"administrator", "creator"} and result.get("type") == "channel":
        recommendations.append("برای انتشار در کانال، ربات باید Administrator باشد.")

    lines = [
        "🧪 تست سلامت ربات و مقصد",
        "",
        f"🤖 ربات: @{me.get('username', 'unknown')}",
        f"🆔 Bot ID: {me.get('id', 'unknown')}",
        f"🎯 مقصد: {DESTINATION}",
        f"📌 نوع مقصد: {result.get('type', 'unknown')}",
        f"👤 وضعیت ربات در مقصد: {status}",
        "",
        "✅ Bot API پاسخ می‌دهد.",
        "✅ مقصد قابل شناسایی است.",
        "ℹ️ هیچ محتوایی ارسال نشد.",
    ]
    if recommendations:
        lines.extend(["", "🚨 موارد نیازمند اصلاح:"] + [f"• {x}" for x in recommendations])
    else:
        lines.extend(["", "✅ دسترسی پایه مناسب است."])
    return "\n".join(lines)


def _command(update: dict[str, Any]) -> str | None:
    text = str((update.get("message") or {}).get("text") or "").strip()
    return text.split()[0].split("@", 1)[0].lower() if text.startswith("/") else None


def poll_owner_commands() -> bool:
    token = _config()
    state = _load_json(OWNER_STATE_PATH)
    offset = int(state.get("update_offset", 0) or 0)
    response = telegram_call(token, "getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})
    updates = response.get("result", [])
    changed = False

    me = telegram_call(token, "getMe").get("result", {})
    if me.get("username") != state.get("bot_username"):
        state["bot_username"] = f"@{me.get('username', 'unknown')}"
        state["bot_id"] = me.get("id")
        changed = True

    for update in updates:
        update_id = int(update.get("update_id", 0))
        state["update_offset"] = max(int(state.get("update_offset", 0) or 0), update_id + 1)
        changed = True

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        sender_id = str(chat.get("id", "")).strip()
        if chat.get("type") != "private" or not sender_id:
            continue

        command = _command(update)
        if not command:
            continue

        owner_id = str(state.get("owner_chat_id", "")).strip()

        if command == "/claim":
            if owner_id:
                if owner_id == sender_id:
                    send_owner(sender_id, "✅ این گفت‌وگو قبلاً به‌عنوان پنل مالک ثبت شده است.\n\n" + OWNER_HELP)
                else:
                    send_owner(sender_id, "⛔ پنل مالک قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                state["owner_chat_id"] = sender_id
                state["owner_username"] = chat.get("username")
                state["claimed_at"] = datetime.now(TZ).isoformat()
                send_owner(sender_id, "✅ این گفت‌وگو با موفقیت به‌عنوان پنل مالک ثبت شد.\n\n" + OWNER_HELP)
            continue

        if not owner_id or sender_id != owner_id:
            # Do not reveal whether an owner exists or expose management details.
            send_owner(sender_id, "این ربات برای انتشار محتوای ClimaVids تنظیم شده است.")
            continue

        try:
            if command == "/help":
                send_owner(sender_id, OWNER_HELP)
            elif command in {"/status", "/report"}:
                send_owner(sender_id, build_report())
            elif command == "/logs":
                send_owner(sender_id, build_logs_summary())
            elif command == "/test":
                send_owner(sender_id, build_test_report())
            else:
                send_owner(sender_id, "❓ دستور ناشناخته است. /help را ارسال کنید.")
        except Exception as exc:
            send_owner(sender_id, f"🚨 خطا در اجرای دستور مالک\n\n{type(exc).__name__}: {exc}")

    if changed:
        _save_json(OWNER_STATE_PATH, state)
    return changed


def send_scheduled_report(report_type: str) -> None:
    state = _load_json(OWNER_STATE_PATH)
    owner_id = str(state.get("owner_chat_id", "")).strip()
    if not owner_id:
        return

    now = datetime.now(TZ)
    key = f"{now:%Y-%m-%d}|{report_type}"
    sent_reports = state.get("sent_reports", [])
    if key in sent_reports:
        return

    title = "☀️ گزارش صبحگاهی ClimaVids" if report_type == "morning" else "🌙 گزارش شبانه ClimaVids"
    send_owner(owner_id, f"{title}\n\n{build_report()}\n\nبرای جزئیات: /logs")
    sent_reports.append(key)
    state["sent_reports"] = sent_reports[-180:]
    _save_json(OWNER_STATE_PATH, state)
