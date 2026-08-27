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
ربات را اضافه و Administrator کنید، سپس /setup را بزنید.

⚙️ فرمان‌های مدیر:
/setup — تنظیمات همین مقصد
/posts 1 — روزانه ۱ پست
/posts 2 — روزانه ۲ پست
/posts 3 — روزانه ۳ پست
/times 10:00 — زمان ارسال
/times 10:00 20:00 — دو زمان ارسال
/on — فعال‌سازی
/off — توقف موقت

🔒 گزارش شبکه و اطلاعات فنی فقط برای مالک ربات است."""
OWNER_HELP = """🔐 پنل خصوصی مالک ContentSenderTelegram

/status — وضعیت کلی
/report — گزارش کامل
/network — فهرست مقصدها
/logs — لاگ و خطاها
/health — سلامت شبکه
/test — تست Bot و کانال اصلی بدون ارسال محتوا
/run — اجرای دستی انتشار اکنون

/claim — ثبت اولیه این گفت‌وگو به عنوان پنل مالک"""


def _token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
    return token


def telegram_call(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    r = requests.post(f"https://api.telegram.org/bot{_token()}/{method}", json=payload or {}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram {method} failed"))
    return data


def send_message(chat_id: int | str, text: str) -> dict[str, Any]:
    return telegram_call("sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def _public_state() -> dict[str, Any]:
    p = Path("data/state.json")
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _owner_id() -> str:
    return str(load_private().get("owner_chat_id") or "")


def is_owner(chat_id: int | str) -> bool:
    owner = _owner_id()
    return bool(owner) and str(chat_id) == owner


def build_report() -> str:
    private = load_private(); public = _public_state()
    metrics = public.get("metrics", {}) if isinstance(public.get("metrics"), dict) else {}
    published = public.get("published", [])
    active = [x for x in private.get("destinations", {}).values() if x.get("active")]
    return (f"📊 گزارش ContentSenderTelegram\n\n🕒 {datetime.now(TZ):%Y-%m-%d %H:%M:%S} تهران\n"
            f"🤖 {private.get('bot_username','نامشخص')}\n🌐 مقصدهای فعال: {len(active)}\n"
            f"👥 گروه‌ها: {sum(x.get('type') in {'group','supergroup'} for x in active)}\n"
            f"📣 کانال‌ها: {sum(x.get('type') == 'channel' for x in active)}\n"
            f"✅ انتشار ثبت‌شده: {len(published)}\n📥 آیتم خام: {metrics.get('last_raw_items','نامشخص')}\n"
            f"🎯 کاندیدها: {metrics.get('last_candidates','نامشخص')}\n✅ موفق: {metrics.get('last_sent','نامشخص')}\n"
            f"❌ ناموفق: {metrics.get('last_failed','نامشخص')}")


def build_network_report() -> str:
    active = [x for x in load_private().get("destinations", {}).values() if x.get("active")]
    lines = ["🌐 گزارش شبکه ClimaVids", "", f"مقصدهای فعال: {len(active)}", ""]
    for i, x in enumerate(sorted(active, key=lambda z: str(z.get("title", "")).casefold()), 1):
        kind = "کانال" if x.get("type") == "channel" else "گروه"
        lines.append(f"{i}. {x.get('title','بدون نام')} — {kind} — {x.get('posts_per_day',1)} پست/روز — {', '.join(x.get('times',[]))}")
    if not active:
        lines.append("هنوز مقصد فعالی ثبت نشده است.")
    return "\n".join(lines)


def build_logs() -> str:
    m = _public_state().get("metrics", {})
    if not isinstance(m, dict): m = {}
    errors = m.get("errors", []) if isinstance(m.get("errors"), list) else []
    out = ["🧾 لاگ ContentSenderTelegram", "", f"آخرین اجرا: {m.get('last_run','نامشخص')}",
           f"نتیجه: {m.get('last_result','نامشخص')}", f"منابع: {m.get('last_sources','نامشخص')}",
           f"خام: {m.get('last_raw_items','نامشخص')}", f"یکتا: {m.get('last_unique_items','نامشخص')}",
           f"کاندید: {m.get('last_candidates','نامشخص')}", f"انتخاب: {m.get('last_selected','نامشخص')}",
           f"موفق: {m.get('last_sent','نامشخص')}", f"ناموفق: {m.get('last_failed','نامشخص')}", ""]
    out.append("آخرین خطاها:") if errors else out.append("✅ خطای ثبت‌شده‌ای وجود ندارد.")
    out.extend(f"• {e}" for e in errors[-10:])
    return "\n".join(out)


def build_test() -> str:
    lines = ["🧪 تست اتصال", ""]
    try:
        me = telegram_call("getMe")["result"]
        lines.append(f"✅ Bot: @{me.get('username','unknown')} | ID: {me.get('id')}")
    except Exception as exc:
        return "\n".join(lines + [f"❌ Bot API: {type(exc).__name__}: {exc}"])
    try:
        chat = telegram_call("getChat", {"chat_id": DESTINATION})["result"]
        member = telegram_call("getChatMember", {"chat_id": DESTINATION, "user_id": me["id"]})["result"]
        lines += [f"✅ مقصد: {chat.get('title', DESTINATION)}", f"🤖 وضعیت: {member.get('status','unknown')}",
                  f"✍️ امکان ارسال: {'بله' if member.get('can_post_messages') is not False else 'خیر'}"]
    except Exception as exc:
        lines.append(f"❌ مقصد اصلی: {type(exc).__name__}: {exc}")
    lines.append("📌 این تست هیچ محتوایی منتشر نمی‌کند.")
    return "\n".join(lines)


def _parse_command(text: str) -> tuple[str | None, list[str]]:
    parts = text.strip().split()
    if not parts or not parts[0].startswith("/"): return None, []
    return parts[0].split("@", 1)[0].lower(), parts[1:]


def command_for_update(update: dict[str, Any]) -> str | None:
    msg = update.get("message") or update.get("channel_post") or {}
    return _parse_command(str(msg.get("text") or ""))[0]


def _admin_for_destination(chat_id: int, user_id: int) -> bool:
    return telegram_call("getChatMember", {"chat_id": chat_id, "user_id": user_id})["result"].get("status") in {"administrator", "creator"}


def _run_manual_publish(chat_id: int) -> None:
    send_message(chat_id, "⏳ اجرای دستی شروع شد؛ خبرها جمع‌آوری و محتوای منتخب آماده می‌شود...")
    try:
        from climavids.distribution import publish_due
        result = publish_due(_token())
        send_message(chat_id, "✅ اجرا تمام شد.\n\n" + f"مقصدهای آماده: {result.get('destinations_due',0)}\n" +
                      f"تلاش: {result.get('attempted',0)}\n✅ موفق: {result.get('sent',0)}\n❌ ناموفق: {result.get('failed',0)}")
    except Exception as exc:
        send_message(chat_id, f"❌ اجرای دستی شکست خورد:\n{type(exc).__name__}: {exc}")


def _handle_destination(update: dict[str, Any], chat: dict[str, Any], command: str, args: list[str]) -> None:
    chat_id = int(chat["id"])
    if command == "/help": send_message(chat_id, PUBLIC_HELP); return
    sender = (update.get("message") or {}).get("from") or {}
    if not sender or not _admin_for_destination(chat_id, int(sender.get("id", 0))):
        send_message(chat_id, "ℹ️ این فرمان فقط برای مدیران همین مقصد است."); return
    if not get_destination(chat_id): register_destination(chat, "administrator")
    if command == "/setup":
        e = get_destination(chat_id)
        send_message(chat_id, f"⚙️ تنظیمات این مقصد\n\nوضعیت: {'فعال ✅' if e.get('active') else 'متوقف ⏸'}\nتعداد: {e.get('posts_per_day',1)} در روز\nساعت‌ها: {', '.join(e.get('times',[]))}\n\nنمونه: /posts 2 و سپس /times 10:00 20:00"); return
    if command == "/posts":
        if len(args)!=1 or not args[0].isdigit(): send_message(chat_id, f"❌ شکل صحیح: /posts 2\nمحدوده 1 تا {MAX_POSTS}"); return
        try: e=update_settings(chat_id, posts_per_day=int(args[0])); send_message(chat_id, f"✅ روزانه {e['posts_per_day']} پست تنظیم شد.")
        except Exception as exc: send_message(chat_id, f"❌ {exc}")
        return
    if command == "/times":
        e=get_destination(chat_id); count=int(e.get("posts_per_day",1)) if e else 1
        if len(args)!=count: send_message(chat_id, f"❌ برای {count} پست دقیقاً {count} زمان بدهید."); return
        try: e=update_settings(chat_id,times=args); send_message(chat_id,"✅ زمان‌ها ثبت شد: "+", ".join(e["times"]))
        except Exception as exc: send_message(chat_id,f"❌ {exc}")
        return
    if command in {"/on","/off"}:
        data=load_private(); e=data.setdefault("destinations",{}).get(str(chat_id))
        if not e: send_message(chat_id,"⚠️ مقصد هنوز ثبت نشده است. ربات را Administrator کنید."); return
        e["active"]=command=="/on"; e["updated_at"]=datetime.now(TZ).isoformat(); save_private(data)
        send_message(chat_id,"✅ ارسال فعال شد." if command=="/on" else "⏸ ارسال متوقف شد."); return
    send_message(chat_id,"❓ فرمان ناشناخته است. /help را بزنید.")


def poll_updates() -> bool:
    telegram_call("deleteWebhook", {"drop_pending_updates": False})
    private=load_private(); offset=int(private.get("update_offset",0) or 0)
    updates=telegram_call("getUpdates", {"offset":offset,"timeout":0,"allowed_updates":["message","my_chat_member","channel_post"]})["result"]
    me=telegram_call("getMe")["result"]; private["bot_id"]=me.get("id"); private["bot_username"]=f"@{me.get('username','unknown')}"; changed=False
    for update in updates:
        uid=int(update.get("update_id",0)); private["update_offset"]=max(int(private.get("update_offset",0) or 0),uid+1); changed=True
        membership=update.get("my_chat_member")
        if membership:
            chat=membership.get("chat") or {}; status=(membership.get("new_chat_member") or {}).get("status","unknown")
            if chat.get("type") in {"group","supergroup","channel"}:
                if status in {"administrator","creator"}: register_destination(chat,status,me.get("id"))
                elif status in {"left","kicked"}:
                    d=load_private(); e=d.setdefault("destinations",{}).get(str(chat.get("id")))
                    if e: e["active"]=False; e["status"]=status; save_private(d)
            continue
        msg=update.get("message") or update.get("channel_post") or {}; chat=msg.get("chat") or {}; text=str(msg.get("text") or "")
        if not chat or not text: continue
        command,args=_parse_command(text); ctype=chat.get("type"); cid=int(chat["id"])
        try:
            if ctype=="private":
                owner=_owner_id()
                if command=="/start": send_message(cid, OWNER_HELP if owner and str(cid)==owner else PUBLIC_HELP)
                elif command=="/claim":
                    if owner and owner!=str(cid): send_message(cid,"⛔ پنل مالک قبلاً ثبت شده است.")
                    else:
                        d=load_private(); d["owner_chat_id"]=cid; d["owner_username"]=(msg.get("from") or {}).get("username"); d["claimed_at"]=datetime.now(TZ).isoformat(); save_private(d); send_message(cid,"✅ پنل مالک ثبت شد.\n\n"+OWNER_HELP)
                elif is_owner(cid):
                    actions={"/help":OWNER_HELP,"/status":build_report(),"/report":build_report(),"/network":build_network_report(),"/logs":build_logs(),"/health":build_health(),"/test":build_test()}
                    if command=="/run": _run_manual_publish(cid)
                    else: send_message(cid, actions.get(command,"❓ فرمان ناشناخته است. /help را بزنید."))
                elif command=="/help": send_message(cid,PUBLIC_HELP)
            elif ctype in {"group","supergroup"}: _handle_destination(update,chat,command,args)
        except Exception as exc:
            try:
                if ctype=="private" and is_owner(cid): send_message(cid,f"🚨 خطا در {command}: {type(exc).__name__}: {exc}")
            except Exception: pass
    if changed: save_private(private)
    return changed


def send_scheduled_report(report_type: str) -> None:
    owner=_owner_id()
    if not owner: return
    now=datetime.now(TZ); data=load_private(); key=f"{now:%Y-%m-%d}|{report_type}"; sent=data.setdefault("scheduled_reports",[])
    if key in sent: return
    title="☀️ گزارش صبحگاهی" if report_type=="morning" else "🌙 گزارش شبانه"
    send_message(owner,f"{title}\n\n{build_report()}\n\n/network | /logs | /health"); sent.append(key); data["scheduled_reports"]=sent[-180:]; save_private(data)


def send_failure_alert(run_url: str, workflow: str) -> None:
    owner=_owner_id()
    if not owner: return
    try: send_message(owner,f"🚨 خطا در {workflow}\n\n{run_url}\n\n/logs برای جزئیات")
    except Exception: pass
