from __future__ import annotations

from datetime import datetime
import os
from typing import Any
from zoneinfo import ZoneInfo

import requests

from climavids.config import DESTINATION
from climavids.destinations import (
    MAX_POSTS,
    all_destinations,
    get_destination,
    register_destination,
    update_settings,
)
from climavids.private_state import load as load_private, save as save_private

TZ = ZoneInfo("Asia/Tehran")

OWNER_HELP = """🔐 پنل خصوصی مالک ContentSenderTelegram

گزارش‌های شبکه فقط برای مالک ربات نمایش داده می‌شوند.

دستورات مالک:
/status — وضعیت کلی موتور و آخرین انتشار
/report — گزارش کامل عملکرد
/network — تعداد و نام تمام گروه‌ها/کانال‌های فعال
/logs — لاگ منابع، کاندیدها و خطاهای اخیر
/health — سلامت ربات و مقصدها
/help — راهنمای پنل مالک

دستورات مدیران گروه/کانال:
/help — راهنمای عمومی و تنظیمات
/setup — نمایش تنظیمات مقصد
/posts 1 — یک پست در روز
/posts 2 — دو پست در روز
/posts 3 — سه پست در روز
/times 10:00 20:00 — تعیین ساعت‌های ارسال
/on — فعال‌سازی دریافت محتوای ClimaVids
/off — توقف ارسال در همین مقصد

محتوای منتشرشده برای همه مقصدهای فعال یکسان است؛ هر مقصد زمان‌بندی مستقل خودش را دارد.
"""

PUBLIC_HELP = """🤖 ContentSenderTelegram | محتوای ClimaVids

این ربات می‌تواند محتوای منتخب حوزه آب، هوا، اقلیم و محیط‌زیست را به گروه یا کانال شما ارسال کند.

✅ برای استفاده:
1) ربات را به گروه اضافه کنید.
2) ربات را Administrator کنید و اجازه ارسال پیام بدهید.
3) ربات به‌صورت پیش‌فرض روزانه ۱ پست ارسال می‌کند.
4) مدیر گروه می‌تواند زمان و تعداد پست را تغییر دهد.

دستورات مدیر:
/setup — مشاهده تنظیمات فعلی
/posts 1 تا 3 — تعداد پست روزانه
/times 10:00 20:00 — زمان‌های ارسال
/on — فعال‌سازی
/off — توقف موقت

📌 محتوای این ربات برای توسعه برند ClimaVids و دسترسی آسان‌تر مخاطبان به مطالب علمی و خبری تهیه می‌شود.
"""


def _token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    return token


def telegram_call(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{_token()}/{method}",
        json=payload or {},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram {method} failed"))
    return data


def send_message(chat_id: int | str, text: str) -> dict[str, Any]:
    return telegram_call("sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def build_report() -> str:
    private = load_private()
    state = private
    public_state = _load_public_state()
    metrics = public_state.get("metrics", {}) if isinstance(public_state.get("metrics"), dict) else {}
    schedule = public_state
    published = public_state.get("published", [])
    seen = public_state.get("seen", [])
    last_publication = schedule.get("last_publication")
    last_line = "ثبت نشده"
    if isinstance(last_publication, dict):
        last_line = f"{last_publication.get('date', 'نامشخص')} | {last_publication.get('at', 'نامشخص')}"

    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    groups = [x for x in active if x.get("type") in {"group", "supergroup"}]
    channels = [x for x in active if x.get("type") == "channel"]

    return (
        "📊 گزارش ContentSenderTelegram\n\n"
        f"🕒 زمان: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} تهران\n"
        f"🤖 ربات: {private.get('bot_username', 'نامشخص')}\n"
        f"👥 گروه‌های فعال: {len(groups)}\n"
        f"📣 کانال‌های فعال: {len(channels)}\n"
        f"🌐 مجموع مقصدهای فعال: {len(active)}\n"
        f"✅ انتشارهای ثبت‌شده: {len(published)}\n"
        f"👁 موارد دیده‌شده: {len(seen)}\n"
        f"📤 آخرین انتشار: {last_line}\n"
        f"📥 آخرین آیتم خام: {metrics.get('last_raw_items', 'نامشخص')}\n"
        f"🎯 آخرین کاندیدها: {metrics.get('last_candidates', 'نامشخص')}\n"
        f"⚠️ خطاهای منابع: {metrics.get('last_source_errors', 'نامشخص')}\n"
    )


def build_network_report() -> str:
    private = load_private()
    destinations = list(private.get("destinations", {}).values())
    active = [x for x in destinations if x.get("active")]
    lines = [
        "🌐 شبکه مقصدهای ContentSenderTelegram",
        "",
        f"تعداد مقصدهای فعال: {len(active)}",
        f"گروه‌ها: {sum(x.get('type') in {'group', 'supergroup'} for x in active)}",
        f"کانال‌ها: {sum(x.get('type') == 'channel' for x in active)}",
        "",
        "فهرست مقصدها:",
    ]
    if not active:
        lines.append("— هنوز گروه یا کانال فعالی ثبت نشده است.")
    for i, entry in enumerate(sorted(active, key=lambda x: str(x.get("title", "")).casefold()), 1):
        kind = "کانال" if entry.get("type") == "channel" else "گروه"
        times = ", ".join(entry.get("times", []))
        lines.append(f"{i}. {entry.get('title', 'بدون نام')} | {kind} | {entry.get('posts_per_day', 1)} پست/روز | {times}")
    return "\n".join(lines)


def build_logs() -> str:
    public_state = _load_public_state()
    metrics = public_state.get("metrics", {}) if isinstance(public_state.get("metrics"), dict) else {}
    errors = metrics.get("errors", []) if isinstance(metrics.get("errors"), list) else []
    lines = [
        "🧾 لاگ ContentSenderTelegram",
        "",
        f"آخرین اجرا: {metrics.get('last_run', 'نامشخص')}",
        f"نتیجه: {metrics.get('last_result', 'نامشخص')}",
        f"منابع فعال: {metrics.get('last_sources', 'نامشخص')}",
        f"آیتم خام: {metrics.get('last_raw_items', 'نامشخص')}",
        f"آیتم یکتا: {metrics.get('last_unique_items', 'نامشخص')}",
        f"کاندیدها: {metrics.get('last_candidates', 'نامشخص')}",
        f"انتخاب‌شده: {metrics.get('last_selected', 'نامشخص')}",
        f"خطای منابع: {metrics.get('last_source_errors', 0)}",
    ]
    if errors:
        lines.append("\nآخرین خطاها:")
        lines.extend(f"• {x}" for x in errors[-10:])
    return "\n".join(lines)


def _load_public_state() -> dict[str, Any]:
    from pathlib import Path
    import json
    path = Path("data/state.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _is_admin(chat_id: int, user_id: int) -> bool:
    member = telegram_call("getChatMember", {"chat_id": chat_id, "user_id": user_id}).get("result", {})
    return member.get("status") in {"administrator", "creator"}


def _parse_command(text: str) -> tuple[str | None, list[str]]:
    parts = text.strip().split()
    if not parts or not parts[0].startswith("/"):
        return None, []
    return parts[0].split("@", 1)[0].lower(), parts[1:]


def _handle_group_command(update: dict[str, Any], chat: dict[str, Any], command: str, args: list[str]) -> None:
    chat_id = int(chat["id"])
    sender = (update.get("message") or {}).get("from") or {}
    user_id = int(sender.get("id", 0))
    if command == "/help":
        send_message(chat_id, PUBLIC_HELP)
        return
    if not _is_admin(chat_id, user_id):
        send_message(chat_id, "ℹ️ این دستور فقط برای مدیران این گروه/کانال در دسترس است.")
        return
    if command == "/setup":
        entry = get_destination(chat_id)
        if not entry:
            send_message(chat_id, "⚠️ مقصد هنوز ثبت نشده است؛ مطمئن شوید ربات Administrator است و دوباره تلاش کنید.")
            return
        send_message(chat_id, f"⚙️ تنظیمات فعلی\n\nپست روزانه: {entry['posts_per_day']}\nساعت‌ها: {', '.join(entry['times'])}\nوضعیت: {'فعال' if entry['active'] else 'غیرفعال'}\n\nبرای تغییر از /posts و /times استفاده کنید.")
        return
    if command == "/posts":
        if len(args) != 1 or not args[0].isdigit():
            send_message(chat_id, f"❌ نمونه صحیح: /posts 2\nتعداد مجاز: 1 تا {MAX_POSTS}")
            return
        try:
            entry = update_settings(chat_id, posts_per_day=int(args[0]))
            send_message(chat_id, f"✅ تعداد انتشار به {entry['posts_per_day']} پست در روز تغییر کرد.\nساعت‌ها: {', '.join(entry['times'])}")
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return
    if command == "/times":
        try:
            entry = get_destination(chat_id)
            count = int(entry.get("posts_per_day", 1)) if entry else 1
            if len(args) != count:
                raise ValueError(f"برای {count} پست، دقیقاً {count} ساعت وارد کنید. مثال: /times 20:00")
            entry = update_settings(chat_id, times=args)
            send_message(chat_id, f"✅ زمان‌های ارسال ثبت شد: {', '.join(entry['times'])}")
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return
    if command == "/on":
        data = load_private()
        entry = data.setdefault("destinations", {}).get(str(chat_id))
        if entry:
            entry["active"] = True
            entry["updated_at"] = datetime.now(TZ).isoformat()
            save_private(data)
            send_message(chat_id, "✅ دریافت محتوای ClimaVids دوباره فعال شد.")
        return
    if command == "/off":
        data = load_private()
        entry = data.setdefault("destinations", {}).get(str(chat_id))
        if entry:
            entry["active"] = False
            entry["updated_at"] = datetime.now(TZ).isoformat()
            save_private(data)
            send_message(chat_id, "⏸ ارسال محتوا در این مقصد متوقف شد. هر زمان خواستید /on را بزنید.")
        return


def poll_updates() -> bool:
    private = load_private()
    offset = int(private.get("update_offset", 0) or 0)
    response = telegram_call("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message", "my_chat_member"]})
    updates = response.get("result", [])
    changed = False

    me = telegram_call("getMe").get("result", {})
    bot_id = me.get("id")
    private["bot_id"] = bot_id
    private["bot_username"] = f"@{me.get('username', 'unknown')}"

    for update in updates:
        update_id = int(update.get("update_id", 0))
        private["update_offset"] = max(int(private.get("update_offset", 0) or 0), update_id + 1)
        changed = True

        my_member = update.get("my_chat_member")
        if my_member:
            chat = my_member.get("chat") or {}
            new_member = my_member.get("new_chat_member") or {}
            status = new_member.get("status", "unknown")
            if chat.get("type") in {"group", "supergroup", "channel"}:
                if status in {"administrator", "creator"}:
                    register_destination(chat, status, bot_id)
                    if chat.get("id") != -100:
                        try:
                            send_message(chat["id"], f"👋 سلام! من ربات انتشار محتوای ClimaVids هستم.\n\n{PUBLIC_HELP}")
                        except Exception:
                            pass
                elif status in {"left", "kicked"}:
                    from climavids.destinations import remove_destination
                    remove_destination(chat.get("id"), status)
            continue

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        text = str(message.get("text") or "").strip()
        if not text:
            continue
        command, args = _parse_command(text)
        if not command:
            continue

        sender_id = int((message.get("from") or {}).get("id", 0))
        chat_id = int(chat.get("id", 0))
        chat_type = chat.get("type")

        owner_id = str(private.get("owner_chat_id") or "")
        if chat_type == "private":
            if command == "/claim":
                if owner_id and owner_id != str(chat_id):
                    send_message(chat_id, "⛔ پنل مالک قبلاً فعال شده است.")
                elif not owner_id:
                    private["owner_chat_id"] = chat_id
                    private["owner_username"] = (message.get("from") or {}).get("username")
                    private["claimed_at"] = datetime.now(TZ).isoformat()
                    send_message(chat_id, "✅ این گفت‌وگوی خصوصی به‌عنوان پنل مالک ثبت شد.\n\n" + OWNER_HELP)
                else:
                    send_message(chat_id, "✅ این گفت‌وگو از قبل پنل مالک است.\n\n" + OWNER_HELP)
                continue

            if owner_id and str(chat_id) == owner_id:
                if command == "/help":
                    send_message(chat_id, OWNER_HELP)
                elif command == "/status":
                    send_message(chat_id, build_report())
                elif command == "/report":
                    send_message(chat_id, build_report())
                elif command == "/network":
                    send_message(chat_id, build_network_report())
                elif command == "/logs":
                    send_message(chat_id, build_logs())
                elif command == "/health":
                    send_message(chat_id, build_report() + "\n\n✅ مقصد پیش‌فرض: " + DESTINATION)
                else:
                    send_message(chat_id, "❓ دستور ناشناخته است. /help را بزنید.")
            else:
                if command == "/help":
                    send_message(chat_id, PUBLIC_HELP)
                else:
                    send_message(chat_id, "ℹ️ برای راهنمای استفاده از ربات /help را بزنید.")
            continue

        if chat_type in {"group", "supergroup", "channel"}:
            try:
                _handle_group_command(update, chat, command, args)
            except Exception as exc:
                try:
                    send_message(chat_id, f"❌ خطای اجرای دستور: {type(exc).__name__}: {exc}")
                except Exception:
                    pass

    if changed:
        save_private(private)
    return changed


def send_scheduled_report(report_type: str) -> None:
    private = load_private()
    owner_id = str(private.get("owner_chat_id") or "")
    if not owner_id:
        return
    now = datetime.now(TZ)
    key = f"{now:%Y-%m-%d}|{report_type}"
    sent = private.setdefault("scheduled_reports", [])
    if key in sent:
        return
    title = "☀️ گزارش صبحگاهی ContentSenderTelegram" if report_type == "morning" else "🌙 گزارش شبانه ContentSenderTelegram"
    send_message(owner_id, f"{title}\n\n{build_report()}\n\nبرای لیست مقصدها: /network\nبرای جزئیات فنی: /logs")
    sent.append(key)
    private["scheduled_reports"] = sent[-180:]
    save_private(private)
