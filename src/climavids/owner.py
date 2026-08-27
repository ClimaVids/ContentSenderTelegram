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

این ربات برای گروه‌ها و کانال‌ها محتوای منتخب آب، هوا، اقلیم و محیط‌زیست را از طریق ClimaVids منتشر می‌کند.

✅ شروع سریع برای مدیران:
• ربات را به گروه اضافه و Administrator کنید.
• ربات را Administrator کنید و اجازه ارسال پیام بدهید.
• ربات به‌صورت پیش‌فرض روزانه ۱ پست می‌فرستد.
• مدیر هر مقصد می‌تواند تعداد و زمان ارسال را تغییر دهد.

⚙️ تنظیمات مدیر:
/setup — مشاهده تنظیمات فعلی
/posts 1 — روزانه ۱ پست
/posts 2 — روزانه ۲ پست
/posts 3 — روزانه ۳ پست
/times 10:00 20:00 — تعیین ساعت‌های ارسال
/on — فعال‌سازی ارسال
/off — توقف موقت ارسال

📌 نکات:
• محتوای منتشرشده در مقصدهای فعال یکسان است؛ زمان‌بندی هر مقصد مستقل است.
• ربات در پیام‌های عادی کاربران دخالت نمی‌کند.
• گزارش شبکه، نام مقصدهای دیگر، آمار کل و خطاهای فنی فقط برای مالک ربات محفوظ است.

برای مشاهده تنظیمات همین مقصد /setup را بزنید."""

OWNER_HELP = """🔐 پنل خصوصی مالک ContentSenderTelegram

داده‌های شبکه و گزارش‌های مهم فقط در این پنل خصوصی قابل مشاهده‌اند.

/status — وضعیت کلی سیستم
/report — گزارش کامل عملکرد و آمار
/network — تعداد و نام گروه‌ها و کانال‌های فعال
/logs — جزئیات فنی، منابع و خطاهای اخیر
/health — بررسی سلامت ربات و همه مقصدها
/help — راهنمای مالک

مدیران مقصدها فقط تنظیمات همان مقصد را می‌بینند."""


def _token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    return token


def telegram_call(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"https://api.telegram.org/bot{_token()}/{method}", json=payload or {}, timeout=25)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram {method} failed"))
    return data


def send_message(chat_id: int | str, text: str) -> dict[str, Any]:
    return telegram_call("sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def _public_state() -> dict[str, Any]:
    path = Path("data/state.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_report() -> str:
    private = load_private()
    public = _public_state()
    metrics = public.get("metrics", {}) if isinstance(public.get("metrics"), dict) else {}
    published = public.get("published", [])
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    groups = [x for x in active if x.get("type") in {"group", "supergroup"}]
    channels = [x for x in active if x.get("type") == "channel"]
    last = public.get("last_publication") or {}
    last_pub = last.get("at", "ثبت نشده") if isinstance(last, dict) else "ثبت نشده"
    return (
        "📊 گزارش ContentSenderTelegram\n\n"
        f"🕒 {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} تهران\n"
        f"🤖 {private.get('bot_username', 'نامشخص')}\n"
        f"🌐 مقصدهای فعال: {len(active)}\n"
        f"👥 گروه‌ها: {len(groups)}\n"
        f"📣 کانال‌ها: {len(channels)}\n"
        f"✅ انتشارهای ثبت‌شده: {len(published)}\n"
        f"📥 آیتم خام آخرین اجرا: {metrics.get('last_raw_items', 'نامشخص')}\n"
        f"🎯 کاندیدهای آخرین اجرا: {metrics.get('last_candidates', 'نامشخص')}\n"
        f"⚠️ خطای منابع: {metrics.get('last_source_errors', 'نامشخص')}\n"
        f"📤 آخرین انتشار: {last_pub}"
    )


def build_network_report() -> str:
    private = load_private()
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    lines = [
        "🌐 گزارش شبکه ContentSenderTelegram",
        "",
        f"✅ مقصدهای فعال: {len(active)}",
        f"👥 گروه‌های فعال: {sum(x.get('type') in {'group', 'supergroup'} for x in active)}",
        f"📣 کانال‌های فعال: {sum(x.get('type') == 'channel' for x in active)}",
        "",
    ]
    if not active:
        lines.append("هنوز هیچ گروه یا کانال فعالی ثبت نشده است.")
        return "\n".join(lines)
    for i, entry in enumerate(sorted(active, key=lambda x: str(x.get("title", "")).casefold()), 1):
        kind = "کانال" if entry.get("type") == "channel" else "گروه"
        username = f" | @{entry['username']}" if entry.get("username") else ""
        lines.append(f"{i}. {entry.get('title', 'بدون نام')} ({kind}){username} — {entry.get('posts_per_day', 1)} پست/روز — {', '.join(entry.get('times', []))}")
    return "\n".join(lines)


def build_logs() -> str:
    public = _public_state()
    metrics = public.get("metrics", {}) if isinstance(public.get("metrics"), dict) else {}
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
    else:
        lines.append("\n✅ خطای ثبت‌شده‌ای وجود ندارد.")
    return "\n".join(lines)


def build_health() -> str:
    private = load_private()
    lines = ["🩺 سلامت ContentSenderTelegram", ""]
    try:
        me = telegram_call("getMe").get("result", {})
        lines.append(f"✅ Bot API: سالم | @{me.get('username', 'unknown')} | ID {me.get('id', 'unknown')}")
    except Exception as exc:
        return "\n".join(lines + [f"❌ Bot API: {type(exc).__name__}: {exc}"])
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    ok = fail = 0
    for entry in active:
        try:
            target = telegram_call("getChat", {"chat_id": int(entry["chat_id"]) }).get("result", {})
            member = telegram_call("getChatMember", {"chat_id": int(entry["chat_id"]), "user_id": me["id"]}).get("result", {})
            status = member.get("status", "unknown")
            if status in {"administrator", "creator"}:
                ok += 1
            else:
                fail += 1
                lines.append(f"⚠️ {target.get('title') or entry.get('title')}: Bot = {status}")
        except Exception as exc:
            fail += 1
            lines.append(f"❌ {entry.get('title')}: {type(exc).__name__}: {exc}")
    lines.append("")
    lines.append(f"مقصدهای سالم: {ok} | نیازمند بررسی: {fail}")
    return "\n".join(lines)


def _parse_command(text: str) -> tuple[str | None, list[str]]:
    parts = text.strip().split()
    if not parts or not parts[0].startswith("/"):
        return None, []
    return parts[0].split("@", 1)[0].lower(), parts[1:]


def _admin_for_group(chat_id: int, user_id: int) -> bool:
    result = telegram_call("getChatMember", {"chat_id": chat_id, "user_id": user_id}).get("result", {})
    return result.get("status") in {"administrator", "creator"}


def _handle_destination_command(update: dict[str, Any], chat: dict[str, Any], command: str, args: list[str], channel_post: bool = False) -> None:
    chat_id = int(chat["id"])
    if command == "/help":
        send_message(chat_id, PUBLIC_HELP)
        return
    if channel_post:
        is_admin = True
    else:
        sender = (update.get("message") or {}).get("from") or {}
        is_admin = _admin_for_group(chat_id, int(sender.get("id", 0)))
    if not is_admin:
        send_message(chat_id, "ℹ️ این دستور فقط برای مدیران قابل استفاده است.")
        return
    if command == "/setup":
        entry = get_destination(chat_id)
        if not entry:
            register_destination(chat, "administrator")
            entry = get_destination(chat_id)
        if entry:
            send_message(chat_id, f"⚙️ تنظیمات این مقصد\n\n📌 وضعیت: {'فعال' if entry.get('active') else 'متوقف'}\n📝 تعداد پست: {entry.get('posts_per_day', 1)} در روز\n🕒 ساعت‌ها: {', '.join(entry.get('times', []))}\n\nبرای تغییر: /posts 2 یا /times 20:00")
        return
    if command == "/posts":
        if len(args) != 1 or not args[0].isdigit():
            send_message(chat_id, f"❌ شکل صحیح: /posts 2\nتعداد مجاز: 1 تا {MAX_POSTS}")
            return
        try:
            entry = update_settings(chat_id, posts_per_day=int(args[0]))
            send_message(chat_id, f"✅ تنظیم شد: روزانه {entry['posts_per_day']} پست.\n🕒 ساعت‌ها: {', '.join(entry['times'])}")
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return
    if command == "/times":
        entry = get_destination(chat_id)
        count = int(entry.get("posts_per_day", 1)) if entry else 1
        if len(args) != count:
            example = " ".join(["10:00", "20:00", "22:00"][:count])
            send_message(chat_id, f"❌ برای {count} پست باید دقیقاً {count} زمان وارد کنید.\nمثال: /times {example}")
            return
        try:
            entry = update_settings(chat_id, times=args)
            send_message(chat_id, "✅ زمان‌های ارسال ثبت شد: " + ", ".join(entry["times"]))
        except Exception as exc:
            send_message(chat_id, f"❌ {exc}")
        return
    if command in {"/on", "/off"}:
        data = load_private()
        entry = data.setdefault("destinations", {}).get(str(chat_id))
        if not entry:
            send_message(chat_id, "⚠️ این مقصد هنوز ثبت نشده است؛ ربات را Administrator کنید.")
            return
        entry["active"] = command == "/on"
        entry["updated_at"] = datetime.now(TZ).isoformat()
        save_private(data)
        send_message(chat_id, "✅ ارسال محتوا فعال شد." if command == "/on" else "⏸ ارسال محتوا در این مقصد متوقف شد.")


def poll_updates() -> bool:
    # This bot uses long-polling via GitHub Actions; remove any stale webhook first.
    try:
        telegram_call("deleteWebhook", {"drop_pending_updates": False})
    except Exception:
        pass

    private = load_private()
    offset = int(private.get("update_offset", 0) or 0)
    updates = telegram_call("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message", "my_chat_member", "channel_post"]}).get("result", [])
    changed = False
    me = telegram_call("getMe").get("result", {})
    private["bot_id"] = me.get("id")
    private["bot_username"] = f"@{me.get('username', 'unknown')}"

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
                    entry = register_destination(chat, status, me.get("id"))
                    data = load_private()
                    item = data.setdefault("destinations", {}).setdefault(str(chat["id"]), entry)
                    if not item.get("welcome_sent"):
                        try:
                            send_message(chat["id"], "👋 سلام! ربات انتشار محتوای ClimaVids فعال شد.\n\n" + PUBLIC_HELP)
                            item["welcome_sent"] = True
                            save_private(data)
                        except Exception:
                            pass
                    private = load_private()
                elif status in {"left", "kicked"}:
                    data = load_private()
                    item = data.setdefault("destinations", {}).get(str(chat.get("id")))
                    if item:
                        item["status"] = status
                        item["active"] = False
                        item["updated_at"] = datetime.now(TZ).isoformat()
                        save_private(data)
                    private = data
            continue

        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        text = str(message.get("text") or "").strip()
        if not text or not chat:
            continue
        command, args = _parse_command(text)
        if not command:
            continue
        chat_type = chat.get("type")
        chat_id = int(chat["id"])

        if chat_type == "private":
            owner_id = str(private.get("owner_chat_id") or "")
            if command == "/start":
                send_message(chat_id, OWNER_HELP if owner_id and str(chat_id) == owner_id else PUBLIC_HELP)
                continue
            if command == "/claim":
                if owner_id and owner_id != str(chat_id):
                    send_message(chat_id, "⛔ پنل مالک قبلاً فعال شده است.")
                elif not owner_id:
                    private["owner_chat_id"] = chat_id
                    private["owner_username"] = (message.get("from") or {}).get("username")
                    private["claimed_at"] = datetime.now(TZ).isoformat()
                    send_message(chat_id, "✅ پنل مالک فعال شد.\n\n" + OWNER_HELP)
                else:
                    send_message(chat_id, "✅ این گفت‌وگو پنل مالک است.\n\n" + OWNER_HELP)
                continue
            if owner_id and str(chat_id) == owner_id:
                actions = {
                    "/help": OWNER_HELP,
                    "/status": build_report(),
                    "/report": build_report(),
                    "/network": build_network_report(),
                    "/logs": build_logs(),
                    "/health": build_health(),
                }
                send_message(chat_id, actions.get(command, "❓ دستور ناشناخته است. /help را بزنید."))
            elif command == "/help":
                send_message(chat_id, PUBLIC_HELP)
            continue

        if chat_type in {"group", "supergroup"}:
            try:
                _handle_destination_command(update, chat, command, args)
                private = load_private()
            except Exception as exc:
                try:
                    send_message(chat_id, f"❌ خطا: {type(exc).__name__}: {exc}")
                except Exception:
                    pass
        elif chat_type == "channel":
            try:
                _handle_destination_command(update, chat, command, args, channel_post=True)
                private = load_private()
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
    send_message(owner_id, f"{title}\n\n{build_report()}\n\n/network برای فهرست مقصدها\n/logs برای جزئیات فنی")
    sent.append(key)
    private["scheduled_reports"] = sent[-180:]
    save_private(private)


def send_failure_alert(run_url: str, workflow: str) -> None:
    private = load_private()
    owner_id = str(private.get("owner_chat_id") or "")
    if not owner_id:
        return
    send_message(owner_id, f"🚨 خطا در {workflow}\n\nاجرای خودکار با خطا متوقف شد.\n🔎 گزارش اجرا:\n{run_url}\n\nبرای بررسی سریع /logs را بزنید.")
