from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from climavids.owner import OWNER_HELP, build_report, send_owner
from climavids.pipeline import run
from climavids.publishers.telegram import TelegramPublisher
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
        choices=["dry-run", "publish", "health", "owner-report", "owner-help"],
    )
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    if args.command in {"owner-report", "owner-help"}:
        send_owner(OWNER_HELP if args.command == "owner-help" else build_report())
        return

    if args.command == "health":
        state = JsonState()
        print(
            json.dumps(
                {
                    "ok": True,
                    "published_count": len(state.load().get("published", [])),
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command == "dry-run":
        items = run(dry_run=True, limit=args.limit)
        _record_metrics(
            last_result="dry-run",
            last_candidates=len(items),
            last_selected=len(items),
        )
        print(json.dumps({"generated": len(items)}, ensure_ascii=False))
        return

    if args.command == "publish":
        try:
            items = run(dry_run=False, limit=1)
            if not items:
                _record_metrics(last_result="no_candidate", last_candidates=0, last_selected=0)
                print(
                    json.dumps(
                        {"published": False, "reason": "no_candidate"},
                        ensure_ascii=False,
                    )
                )
                return

            draft = items[0]["draft"]
            _record_metrics(
                last_result="candidate_selected",
                last_candidates=len(items),
                last_selected=1,
                last_score=items[0].get("score"),
            )
            publisher = TelegramPublisher()
            result = publisher.send_text(draft["body"])
            message_id = result.get("result", {}).get("message_id")
            state = JsonState()
            state.mark_published(draft["item_id"], message_id)
            state.mark_seen(draft["item_id"])
            _record_metrics(last_result="published", last_message_id=message_id)
            print(
                json.dumps(
                    {
                        "published": True,
                        "item_id": draft["item_id"],
                        "message_id": message_id,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as exc:
            _record_metrics(last_result="error", last_error=f"{type(exc).__name__}: {exc}")
            raise
