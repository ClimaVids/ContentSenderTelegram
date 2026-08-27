from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from climavids.distribution import publish_due
from climavids.owner import OWNER_HELP, build_report, send_message
from climavids.pipeline import run
from climavids.remote_network import fetch_force_run
from climavids.state import JsonState


def _record_metrics(**values: object) -> None:
    state = JsonState()
    data = state.load()
    metrics = data.setdefault("metrics", {})
    metrics.update(values)
    metrics["last_run"] = datetime.now(timezone.utc).isoformat()
    state.save(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["dry-run", "publish", "publish-network", "health", "owner-report", "owner-help"],
    )
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command in {"owner-report", "owner-help"}:
        from climavids.private_state import load as load_private
        owner = str(load_private().get("owner_chat_id") or "")
        if not owner:
            raise RuntimeError("owner is not claimed; send /claim to the bot first")
        send_message(owner, OWNER_HELP if args.command == "owner-help" else build_report())
        return

    if args.command == "health":
        state = JsonState()
        print(json.dumps({"ok": True, "published_count": len(state.load().get("published", []))}, ensure_ascii=False))
        return

    if args.command == "dry-run":
        items = run(dry_run=True, limit=args.limit)
        _record_metrics(last_result="dry-run", last_candidates=len(items), last_selected=len(items))
        print(json.dumps({"generated": len(items)}, ensure_ascii=False))
        return

    if args.command == "publish-network":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
        remote_force = fetch_force_run(token)
        force = bool(args.force or (remote_force or {}).get("pending"))
        result = publish_due(token, force=force)
        _record_metrics(
            last_result="network-publish",
            last_due_destinations=result["destinations_due"],
            last_attempted=result["attempted"],
            last_sent=result["sent"],
            last_failed=result["failed"],
            last_distribution_errors=result["errors"],
        )
        print(json.dumps(result, ensure_ascii=False))
        if result["failed"]:
            raise RuntimeError("one or more destination deliveries failed")
        return

    if args.command == "publish":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        result = publish_due(token, force=args.force)
        print(json.dumps(result, ensure_ascii=False))
