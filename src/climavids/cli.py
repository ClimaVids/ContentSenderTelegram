from __future__ import annotations

import argparse
import json

from climavids.pipeline import run
from climavids.publishers.telegram import TelegramPublisher
from climavids.state import JsonState


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["dry-run", "publish", "health"])
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    if args.command == "dry-run":
        items = run(dry_run=True, limit=args.limit)
        print(json.dumps({"generated": len(items)}, ensure_ascii=False))
        return

    if args.command == "publish":
        items = run(dry_run=False, limit=1)
        if not items:
            print(json.dumps({"published": False, "reason": "no_candidate"}, ensure_ascii=False))
            return
        draft = items[0]["draft"]
        publisher = TelegramPublisher()
        result = publisher.send_text(draft["body"])
        message_id = result.get("result", {}).get("message_id")
        state = JsonState()
        state.mark_published(draft["item_id"], message_id)
        state.mark_seen(draft["item_id"])
        print(json.dumps({"published": True, "item_id": draft["item_id"], "message_id": message_id}, ensure_ascii=False))
        return

    state = JsonState()
    print(json.dumps({"ok": True, "published_count": len(state.load().get("published", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
