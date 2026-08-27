from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from climavids.config import DESTINATION
from climavids.destinations import MAX_POSTS, get_destination, register_destination, update_settings
from climavids.private_state import load as load_private, save as save_private

TZ = ZoneInfo("Asia/Tehran")

PUBLIC_HELP = """🤖 ContentSenderTelegram | دستیار انتشار محتوای ClimaVids

این ربات محتوای منتخب آب، هواشناسی، اقلیم و محیط‌زیست را برای گروه‌ها و کانال‌هایی که ربات را Administrator کرده‌اند منتشر می‌کند.

🚀 شروع مدیران:
ربات را اضافه و Administrator کنید و سپس /setup را بزنید.

⚙️ فرمان‌های مدیر:
/setup — مشاهده تنظیمات همین مقصد
/posts 1 — روزانه ۱ پست
/posts 2 — روزانه ۲ پست
/posts 3 — روزانه ۳ پست
/times 10:00 — زمان ارسال
/times 10:00 20:00 — دو زمان ارسال
/on — فعال‌سازی
/off — توقف موقت

🔒 آمار شبکه و اطلاعات فنی فقط برای مالک ربات قابل مشاهده است."""

OWNER_HELP = """🔐 پنل خصوصی مالک ContentSenderTelegram

/status — وضعیت کلی
/report — گزارش کامل
/network — فهرست مقصدها
/logs — لاگ و خطاها
/health — سلامت شبکه
/test — تست Bot و کانال اصلی بدون ارسال
/run — اجرای دستی انتشار فوری

/claim — ثبت اولیه این گفت‌وگو به عنوان پنل مالک"""


def _token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
    return token


def telegram_call(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{_token()}/{method}",
        json=payload or {},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram {method} failed"))
    return data


def send_message(chat_id: int | str, text: str) -> dict[str, Any]:
    return telegram_call(
        "sendMessage",
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
    )


def _public_state() -> dict[str, Any]:
    path = Path("data/state.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _owner_id() -> str:
    try:
        return str(load_private().get("owner_chat_id") or "")
    except RuntimeError:
        return ""


def is_owner(chat_id: int | str) -> bool:
    owner = _owner_id()
    return bool(owner) and str(chat_id) == owner


def build_report() -> str:
    private = load_private()
    public = _public_state()
    metrics = public.get("metrics", {}) if isinstance(public.get("metrics"), dict) else {}
    published = public.get("published", [])
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    return (
        "📊 گزارش ContentSenderTelegram\n\n"
        f"🕒 {datetime.now(TZ):%Y-%m-%d %H:%M:%S} تهران\n"
        f"🤖 {private.get('bot_username', 'نامشخص')}\n"
        f"🌐 مقصدهای فعال: {len(active)}\n"
        f"👥 گروه‌ها: {sum(x.get('type') in {'group', 'supergroup'} for x in active)}\n"
        f"📣 کانال‌ها: {sum(x.get('type') == 'channel' for x in active)}\n"
        f"✅ انتشار ثبت‌شده: {len(published)}\n"
        f"📥 آیتم خام: {metrics.get('last_raw_items', 'نامشخص')}\n"
        f"🎯 کاندیدها: {metrics.get('last_candidates', 'نامشخص')}\n"
        f"✅ موفق: {metrics.get('last_sent', 'نامشخص')}\n"
        f"❌ ناموفق: {metrics.get('last_failed', 'نامشخص')}"
    )


def build_network_report() -> str:
    active = [x for x in load_private().get("destinations", {}).values() if x.get("active")]
    lines = [
        "🌐 گزارش شبکه ClimaVids",
        "",
        f"مقصدهای فعال: {len(active)}",
        f"گروه‌ها: {sum(x.get('type') in {'group', 'supergroup'} for x in active)}",
        f"کانال‌ها: {sum(x.get('type') == 'channel' for x in active)}",
        "",
    ]
    for index, entry in enumerate(sorted(active, key=lambda x: str(x.get("title", "")).casefold()), 1):
        kind = "کانال" if entry.get("type") == "channel" else "گروه"
        username = f" | @{entry['username']}" if entry.get("username") else ""
        lines.append(
            f"{index}. {entry.get('title', 'بدون نام')} — {kind}{username} — "
            f"{entry.get('posts_per_day', 1)} پست/روز — {', '.join(entry.get('times', []))}"
        )
    if not active:
        lines.append("هنوز هیچ مقصد فعالی ثبت نشده است.")
    return "\n".join(lines)


def build_logs() -> str:
    metrics = _public_state().get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    errors = metrics.get("errors", []) if isinstance(metrics.get("errors"), list) else []
    lines = [
        "🧾 لاگ ContentSenderTelegram",
        "",
        f"آخرین اجرا: {metrics.get('last_run', 'نامشخص')}",
        f"نتیجه: {metrics.get('last_result', 'نامشخص')}",
        f"منابع: {metrics.get('last_sources', 'نامشخص')}",
        f"خام: {metrics.get('last_raw_items', 'نامشخص')}",
        f"یکتا: {metrics.get('last_unique_items', 'نامشخص')}",
        f"کاندید: {metrics.get('last_candidates', 'نامشخص')}",
        f"انتخاب: {metrics.get('last_selected', 'نامشخص')}",
        f"موفق: {metrics.get('last_sent', 'نامشخص')}",
        f"ناموفق: {metrics.get('last_failed', 'نامشخص')}",
        "",
    ]
    if errors:
        lines.append("آخرین خطاها:")
        lines.extend(f"• {error}" for error in errors[-10:])
    else:
        lines.append("✅ خطای ثبت‌شده‌ای وجود ندارد.")
    return "\n".join(lines)


def build_health() -> str:
    lines = ["🩺 سلامت ContentSenderTelegram", ""]
    try:
        me = telegram_call("getMe")["result"]
        lines.append(f"✅ Bot API: @{me.get('username', 'unknown')} | ID: {me.get('id', 'unknown')}")
    except Exception as exc:
        return "\n".join(lines + [f"❌ Bot API: {type(exc).__name__}: {exc}"])

    private = load_private()
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    healthy = broken = 0
    for entry in active:
        try:
            chat = telegram_call("getChat", {"chat_id": int(entry["chat_id"])})["result"]
            member = telegram_call(
                "getChatMember",
                {"chat_id": int(entry["chat_id"]), "user_id": me["id"]},
            )["result"]
            status = member.get("status", "unknown")
            can_post = member.get("can_post_messages", True)
            if status in {"administrator", "creator"} and can_post is not False:
                healthy += 1
            else:
                broken += 1
                lines.append(f"⚠️ {chat.get('title') or entry.get('title')}: Bot={status}, ارسال={'خیر' if can_post is False else 'بررسی شود'}")
        except Exception as exc:
            broken += 1
            lines.append(f"❌ {entry.get('title', 'مقصد')}: {type(exc).__name__}: {exc}")
    lines += ["", f"مقصدهای سالم: {healthy} | نیازمند بررسی: {broken}"]
    return "\n".join(lines)


def build_test() -> str:
    lines = ["🧪 تست اتصال", ""]
    try:
        me = telegram_call("getMe")["result"]
        lines.append(f"✅ Bot: @{me.get('username', 'unknown')} | ID: {me.get('id')}")
    except Exception as exc:
        return "\n".join(lines + [f"❌ Bot API: {type(exc).__name__}: {exc}"])

    try:
        chat = telegram_call("getChat", {"chat_id": DESTINATION})["result"]
        member = telegram_call(
            "getChatMember", {"chat_id": DESTINATION, "user_id": me["id"]}
        )["result"]
        can_post = member.get("can_post_messages")
        lines.extend(
            [
                f"✅ مقصد اصلی: {chat.get('title', DESTINATION)}",
                f"🤖 وضعیت Bot: {member.get('status', 'unknown')}",
                f"✍️ امکان ارسال: {'بله' if can_post is not False else 'خیر'}",
            ]
        )
    except Exception as exc:
        lines.append(f"❌ مقصد اصلی: {type(exc).__name__}: {exc}")
    lines.append("📌 این تست هیچ محتوایی منتشر نمی‌کند.")
    return "\n".join(lines)


def _parse_command(text: str) -> tuple[str | None, list[str]]:
    parts = text.strip().split()
    if not parts or not parts[0].startswith("/"):
        return None, []
    return parts[0].split("@", 1)[0].lower(), parts[1:]


def command_for_update(update: dict[str, Any]) -> str | None:
    message = update.get("message") or update.get("channel_post") or {}
    return _parse_command(str(message.get("text") or ""))[0]


def _admin_for_destination(chat_id: int, user_id: int) -> bool:
    result = telegram_call("getChatMember", {"chat_id": chat_id, "user_id": user_id})["result"]
    return result.get("status") in {"administrator", "creator"}


def _run_manual_publish(chat_id: int) -> None:
    send_message(chat_id, "⏳ اجرای دستی آغاز شد؛ خبرها در حال جمع‌آوری و آماده‌سازی هستند...")
    try:
        from climavids.distribution import publish_now

        result = publish_now(_token())
        lines = [
            "✅ اجرای دستی پایان یافت.",
            "",
            f"🎯 مقصدها: {result.get('active_destinations', 0)}",
            f"📤 تلاش برای ارسال: {result.get('attempted', 0)}",
            f"✅ ارسال موفق: {result.get('sent', 0)}",
            f"❌ ارسال ناموفق: {result.get('failed', 0)}",
        ]
        if result.get("errors"):
            lines += ["", "خطاها:"] + [f"• {e}" for e in result["errors"][:8]]
        send_message(chat_id, "\n".join(lines))
    except Exception as exc:
        send_message(chat_id, f"❌ اجرای دستی شکست خورد.\n{type(exc).__name__}: {exc}")


def _handle_destination(update: dict[str, Any], chat: dict[str, Any], command: str, args: list[str]) -> None:
    chat_id = int(chat["id"])
    if command == "/help":
        send_message(chat_id, PUBLIC_HELP)
        return
    sender = (update.get("message") or {}).get("from") or {}
    if not sender or not _admin_for_destination(chat_id, int(sender.get("id", 0))):
        send_message(chat_id, "ℹ️ این فرمان فقط برای مدیران همین مقصد است.")
        return
    if not get_destination(chat_id):
        register_destination(chat, "administrator")

    if command == "/setup":
        entry = get_destination(chat_id)
        send_message(
            chat_id,
            "⚙️ تنظیمات این مقصد\n\n"
            f"وضعیت: {'فعال ✅' if entry.get('active') else 'متوقف ⏸'}\n"
            f"تعداد پست: {entry.get('posts_per_day', 1)} در روز\n"
            f"ساعت‌ها: {', '.join(entry.get('times', []))}\n\n"
            "نمونه: /posts 2 سپس /times 10:00 20:00",
        )
        return

    if command == "/posts":
        if len(args) != 1 or not args[0].isdigit():
            send_message(chat_id, f"❌ شکل صحیح: /posts 2\nمحدوده مجاز: 1 تا {MAX_POSTS}")
            return
        try:
            entry = update_settings(chat_id, posts_per_day=int(args[0]))
            send_message(chat_id, f"✅ روزانه {entry['posts_per_day']} پست تنظیم شد.")
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return

    if command == "/times":
        entry = get_destination(chat_id)
        count = int(entry.get("posts_per_day", 1)) if entry else 1
        if len(args) != count:
            examples = ["10:00", "20:00", "22:00"][:count]
            send_message(chat_id, f"❌ برای {count} پست دقیقاً {count} زمان بدهید.\nمثال: /times {' '.join(examples)}")
            return
        try:
            entry = update_settings(chat_id, times=args)
            send_message(chat_id, "✅ زمان‌ها ثبت شد: " + ", ".join(entry["times"]))
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return

    if command in {"/on", "/off"}:
        data = load_private()
        entry = data.setdefault("destinations", {}).get(str(chat_id))
        if not entry:
            send_message(chat_id, "⚠️ مقصد هنوز ثبت نشده است. ربات را Administrator کنید.")
            return
        entry["active"] = command == "/on"
        entry["updated_at"] = datetime.now(TZ).isoformat()
        save_private(data)
        send_message(chat_id, "✅ ارسال فعال شد." if command == "/on" else "⏸ ارسال متوقف شد.")
        return

    send_message(chat_id, "❓ فرمان ناشناخته است. /help را بزنید.")


def poll_updates() -> bool:
    # We intentionally keep long-polling disabled here because GitHub Actions
    # is a short-lived runner. Telegram requires webhook and getUpdates not to
    # be active simultaneously, so clear any webhook before polling.
    telegram_call("deleteWebhook", {"drop_pending_updates": False})
    private = load_private()
    offset = int(private.get("update_offset", 0) or 0)
    updates = telegram_call(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": ["message", "my_chat_member", "channel_post"],
        },
    ).get("result", [])

    me = telegram_call("getMe")["result"]
    private["bot_id"] = me.get("id")
    private["bot_username"] = f"@{me.get('username', 'unknown')}"
    changed = False

    for update in updates:
        update_id = int(update.get("update_id", 0))
        private["update_offset"] = max(int(private.get("update_offset", 0) or 0), update_id + 1)
        changed = True

        membership = update.get("my_chat_member")
        if membership:
            chat = membership.get("chat") or {}
            status = (membership.get("new_chat_member") or {}).get("status", "unknown")
            if chat.get("type") in {"group", "supergroup", "channel"}:
                if status in {"administrator", "creator"}:
                    register_destination(chat, status, me.get("id"))
                    try:
                        entry = get_destination(chat["id"])
                        if entry and not entry.get("welcome_sent") and chat.get("type") != "channel":
                            send_message(int(chat["id"]), "👋 سلام! ربات انتشار محتوای ClimaVids فعال شد.\n\n" + PUBLIC_HELP)
                            data = load_private()
                            data.setdefault("destinations", {}).setdefault(str(chat["id"]), entry)["welcome_sent"] = True
                            save_private(data)
                    except Exception:
                        pass
                elif status in {"left", "kicked"}:
                    data = load_private()
                    entry = data.setdefault("destinations", {}).get(str(chat.get("id")))
                    if entry:
                        entry["active"] = False
                        entry["status"] = status
                        entry["updated_at"] = datetime.now(TZ).isoformat()
                        save_private(data)
            continue

        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        text = str(message.get("text") or "").strip()
        if not chat or not text:
            continue
        command, args = _parse_command(text)
        if not command:
            continue

        chat_type = chat.get("type")
        chat_id = int(chat["id"])
        try:
            if chat_type == "private":
                owner = _owner_id()
                if command == "/start":
                    send_message(chat_id, OWNER_HELP if owner and str(chat_id) == owner else PUBLIC_HELP)
                elif command == "/claim":
                    if owner and owner != str(chat_id):
                        send_message(chat_id, "⛔ پنل مالک قبلاً ثبت شده است.")
                    else:
                        data = load_private()
                        data["owner_chat_id"] = chat_id
                        data["owner_username"] = (message.get("from") or {}).get("username")
                        data["claimed_at"] = datetime.now(TZ).isoformat()
                        save_private(data)
                        send_message(chat_id, "✅ پنل مالک ثبت شد.\n\n" + OWNER_HELP)
                elif is_owner(chat_id):
                    # Lazy dispatch is important: evaluating a dictionary of
                    # function calls caused every command to fail when one
                    # diagnostic function was missing.
                    if command == "/help":
                        response = OWNER_HELP
                    elif command in {"/status", "/report"}:
                        response = build_report()
                    elif command == "/network":
                        response = build_network_report()
                    elif command == "/logs":
                        response = build_logs()
                    elif command == "/health":
                        response = build_health()
                    elif command == "/test":
                        response = build_test()
                    elif command == "/run":
                        _run_manual_publish(chat_id)
                        response = None
                    else:
                        response = "❓ فرمان ناشناخته است. /help را بزنید."
                    if response:
                        send_message(chat_id, response)
                elif command == "/help":
                    send_message(chat_id, PUBLIC_HELP)

            elif chat_type in {"group", "supergroup"}:
                _handle_destination(update, chat, command, args)

        except Exception as exc:
            # Never swallow owner-facing errors.
            try:
                if chat_type == "private" and is_owner(chat_id):
                    send_message(chat_id, f"🚨 خطا در {command}: {type(exc).__name__}: {exc}")
            except Exception:
                pass

    if changed:
        save_private(private)
    return changed


def send_scheduled_report(report_type: str) -> None:
    owner = _owner_id()
    if not owner:
        return
    data = load_private()
    now = datetime.now(TZ)
    key = f"{now:%Y-%m-%d}|{report_type}"
    sent = data.setdefault("scheduled_reports", [])
    if key in sent:
        return
    title = "☀️ گزارش صبحگاهی" if report_type == "morning" else "🌙 گزارش شبانه"
    send_message(owner, f"{title}\n\n{build_report()}\n\n/network | /logs | /health")
    sent.append(key)
    data["scheduled_reports"] = sent[-180:]
    save_private(data)


def send_failure_alert(run_url: str, workflow: str) -> None:
    owner = _owner_id()
    if not owner:
        return
    try:
        send_message(owner, f"🚨 خطا در {workflow}\n\n{run_url}\n\n/logs برای جزئیات")
    except Exception:
        pass
