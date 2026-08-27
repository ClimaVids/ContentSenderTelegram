from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from climavids.config import DESTINATION
from climavids.destinations import active_destinations, delivered, due_destinations, mark_delivered
from climavids.pipeline import run
from climavids.private_state import load as load_private, save as save_private
from climavids.publishers.telegram import TelegramPublisher
from climavids.state import JsonState

TZ = ZoneInfo("Asia/Tehran")


def _slot_key(date: str, slot: int) -> str:
    return f"{date}|slot{slot}"


def _get_or_create_draft(date: str, slot: int) -> dict[str, Any] | None:
    private = load_private()
    cache = private.setdefault("slot_content", {})
    key = _slot_key(date, slot)
    cached = cache.get(key)
    if isinstance(cached, dict) and isinstance(cached.get("draft"), dict) and cached["draft"].get("body"):
        return cached

    items = run(dry_run=False, limit=1)
    if not items:
        return None
    draft = items[0]["draft"]
    cache[key] = {"draft": draft, "created_at": datetime.now(TZ).isoformat()}
    cutoff = datetime.now(TZ) - timedelta(days=14)
    kept: dict[str, Any] = {}
    for k, value in cache.items():
        try:
            stamp = datetime.fromisoformat(k.split("|", 1)[0]).replace(tzinfo=TZ)
            if stamp >= cutoff:
                kept[k] = value
        except (ValueError, TypeError):
            kept[k] = value
    private["slot_content"] = kept
    save_private(private)
    return kept[key]


def ensure_primary_destination(token: str) -> dict[str, Any]:
    publisher = TelegramPublisher(token=token, chat_id=DESTINATION)
    chat = publisher.destination_check().get("result", {})
    membership = publisher.bot_membership().get("result", {})
    status = membership.get("status", "unknown")
    if status not in {"administrator", "creator"}:
        raise RuntimeError("ربات باید در کانال @climavids Administrator باشد.")

    private = load_private()
    destinations = private.setdefault("destinations", {})
    chat_id = str(chat["id"])
    entry = destinations.get(chat_id, {})
    entry.update(
        {
            "chat_id": int(chat["id"]),
            "title": chat.get("title") or "ClimaVids",
            "username": chat.get("username") or "climavids",
            "type": chat.get("type", "channel"),
            "status": status,
            "active": True,
            "posts_per_day": int(entry.get("posts_per_day", 1)),
            "times": entry.get("times", ["20:00"]),
            "is_primary": True,
            "added_at": entry.get("added_at") or datetime.now(TZ).isoformat(),
            "updated_at": datetime.now(TZ).isoformat(),
        }
    )
    destinations[chat_id] = entry
    private["destinations"] = destinations
    save_private(private)
    return entry


def publish_due(token: str) -> dict[str, Any]:
    ensure_primary_destination(token)
    now = datetime.now(TZ)
    jobs = due_destinations(now)

    selected: dict[str, tuple[dict[str, Any], int]] = {}
    for entry, slot in jobs:
        chat_id = str(entry["chat_id"])
        if delivered(now.strftime("%Y-%m-%d"), slot, chat_id):
            continue
        if chat_id not in selected or slot < selected[chat_id][1]:
            selected[chat_id] = (entry, slot)

    attempted = sent = failed = 0
    errors: list[str] = []

    for entry, slot in selected.values():
        attempted += 1
        date = now.strftime("%Y-%m-%d")
        payload = _get_or_create_draft(date, slot)
        if not payload:
            failed += 1
            errors.append(f"{entry.get('title')}: کاندید مناسب پیدا نشد")
            continue
        draft = payload["draft"]
        try:
            result = TelegramPublisher(token=token, chat_id=str(entry["chat_id"])).send_text(draft["body"])
            message_id = int(result.get("result", {}).get("message_id"))
            mark_delivered(date, slot, entry["chat_id"], message_id)
            JsonState().mark_published(draft["item_id"], message_id)
            sent += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{entry.get('title')}: {type(exc).__name__}: {exc}")

    return {
        "now": now.isoformat(),
        "destinations_due": len(selected),
        "attempted": attempted,
        "sent": sent,
        "failed": failed,
        "errors": errors,
        "active_destinations": len(active_destinations()),
    }
