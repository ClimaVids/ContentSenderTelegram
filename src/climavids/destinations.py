from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from climavids.config import DESTINATION
from climavids.private_state import load as load_private, save as save_private
from climavids.publishers.telegram import TelegramError, TelegramPublisher
from climavids.remote_network import fetch_destinations

TZ = ZoneInfo("Asia/Tehran")
DEFAULT_TIMES = ["20:00"]
MIN_POSTS = 1
MAX_POSTS = 3


def _entry_name(chat: dict[str, Any]) -> str:
    return str(chat.get("title") or chat.get("username") or chat.get("first_name") or chat.get("id"))


def _normalise_times(times: list[str]) -> list[str]:
    out: list[str] = []
    for value in times:
        try:
            hh, mm = value.strip().split(":", 1)
            h, m = int(hh), int(mm)
            if 0 <= h <= 23 and 0 <= m <= 59:
                out.append(f"{h:02d}:{m:02d}")
        except (ValueError, AttributeError):
            continue
    return sorted(set(out)) or DEFAULT_TIMES.copy()


def register_destination(chat: dict[str, Any], status: str, bot_id: int | None = None) -> dict[str, Any]:
    data = load_private()
    destinations = data.setdefault("destinations", {})
    chat_id = str(chat.get("id"))
    old = destinations.get(chat_id, {})
    entry = {
        "chat_id": int(chat["id"]),
        "title": _entry_name(chat),
        "username": chat.get("username"),
        "type": chat.get("type", "unknown"),
        "status": status,
        "active": status in {"administrator", "creator"},
        "posts_per_day": int(old.get("posts_per_day", 1)),
        "times": _normalise_times(old.get("times", DEFAULT_TIMES)),
        "added_at": old.get("added_at") or datetime.now(TZ).isoformat(),
        "updated_at": datetime.now(TZ).isoformat(),
        "bot_id": bot_id or old.get("bot_id"),
        "admin_configured": bool(old.get("admin_configured", False)),
    }
    if entry["posts_per_day"] > MAX_POSTS:
        entry["posts_per_day"] = MAX_POSTS
    if len(entry["times"]) != entry["posts_per_day"]:
        entry["times"] = _fill_times(entry["times"], entry["posts_per_day"])
    destinations[chat_id] = entry
    data["destinations"] = destinations
    save_private(data)
    return entry


def _fill_times(times: list[str], count: int) -> list[str]:
    defaults = ["10:00", "20:00", "22:00"]
    merged = list(times)
    for value in defaults:
        if len(merged) >= count:
            break
        if value not in merged:
            merged.append(value)
    return _normalise_times(merged)[:count]


def remove_destination(chat_id: int | str, status: str = "left") -> None:
    data = load_private()
    entry = data.setdefault("destinations", {}).get(str(chat_id))
    if entry:
        entry["status"] = status
        entry["active"] = False
        entry["updated_at"] = datetime.now(TZ).isoformat()
        save_private(data)


def get_destination(chat_id: int | str) -> dict[str, Any] | None:
    return load_private().setdefault("destinations", {}).get(str(chat_id))


def active_destinations(token: str | None = None) -> list[dict[str, Any]]:
    token = token or __import__("os").environ.get("TELEGRAM_BOT_TOKEN", "")
    try:
        remote = fetch_destinations(token)
        if remote is not None:
            return [x for x in remote if x.get("active") and x.get("status") in {"administrator", "creator"}]
    except Exception as exc:
        print(f"REMOTE_DESTINATIONS_ERROR {type(exc).__name__}: {exc}")
    destinations = load_private().setdefault("destinations", {})
    return [x for x in destinations.values() if x.get("active") and x.get("status") in {"administrator", "creator"}]


def all_destinations() -> list[dict[str, Any]]:
    return list(load_private().setdefault("destinations", {}).values())


def update_settings(chat_id: int, *, posts_per_day: int | None = None, times: list[str] | None = None) -> dict[str, Any]:
    data = load_private()
    entry = data.setdefault("destinations", {}).get(str(chat_id))
    if not entry:
        raise TelegramError("این گروه یا کانال هنوز توسط ربات ثبت نشده است.")
    if posts_per_day is not None:
        if not MIN_POSTS <= posts_per_day <= MAX_POSTS:
            raise TelegramError(f"تعداد پست روزانه باید بین {MIN_POSTS} و {MAX_POSTS} باشد.")
        entry["posts_per_day"] = posts_per_day
    if times is not None:
        clean = _normalise_times(times)
        if len(clean) != entry["posts_per_day"]:
            raise TelegramError(f"برای {entry['posts_per_day']} پست، دقیقاً {entry['posts_per_day']} زمان معتبر لازم است.")
        entry["times"] = clean
    entry["admin_configured"] = True
    entry["updated_at"] = datetime.now(TZ).isoformat()
    data["destinations"][str(chat_id)] = entry
    save_private(data)
    return entry


def due_destinations(now: datetime | None = None, token: str | None = None) -> list[tuple[dict[str, Any], int]]:
    now = now or datetime.now(TZ)
    result: list[tuple[dict[str, Any], int]] = []
    for entry in active_destinations(token):
        for slot, value in enumerate(entry.get("times", DEFAULT_TIMES), start=1):
            try:
                hh, mm = map(int, value.split(":"))
            except (ValueError, AttributeError):
                continue
            scheduled = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if now >= scheduled:
                result.append((entry, slot))
    return result


def delivery_key(date: str, slot: int, chat_id: int | str) -> str:
    return f"{date}|slot{slot}|{chat_id}"


def delivered(date: str, slot: int, chat_id: int | str) -> bool:
    return delivery_key(date, slot, chat_id) in load_private().setdefault("delivery", {})


def mark_delivered(date: str, slot: int, chat_id: int | str, message_id: int) -> None:
    data = load_private()
    delivery = data.setdefault("delivery", {})
    delivery[delivery_key(date, slot, chat_id)] = {"message_id": message_id, "at": datetime.now(TZ).isoformat()}
    cutoff = datetime.now(TZ) - timedelta(days=120)
    kept: dict[str, Any] = {}
    for key, value in delivery.items():
        try:
            date_value = key.split("|", 1)[0]
            stamp = datetime.fromisoformat(date_value).replace(tzinfo=TZ)
            if stamp >= cutoff:
                kept[key] = value
        except (ValueError, TypeError):
            kept[key] = value
    data["delivery"] = kept
    save_private(data)


def destination_health(entry: dict[str, Any], token: str) -> dict[str, Any]:
    publisher = TelegramPublisher(token=token, chat_id=str(entry["chat_id"]))
    chat = publisher.destination_check().get("result", {})
    membership = publisher.bot_membership().get("result", {})
    return {
        "title": chat.get("title") or chat.get("username") or entry.get("title"),
        "type": chat.get("type"),
        "status": membership.get("status"),
        "permissions": membership.get("can_post_messages"),
    }
