from __future__ import annotations

import json
from pathlib import Path


class JsonState:
    def __init__(self, path: str = "data/state.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self.path.exists():
            return {"seen": [], "published": [], "metrics": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"seen": [], "published": [], "metrics": {}}

    def save(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def seen(self, item_id: str) -> bool:
        return item_id in set(self.load().get("seen", []))

    def mark_seen(self, item_id: str) -> None:
        data = self.load()
        seen = data.setdefault("seen", [])
        if item_id not in seen:
            seen.append(item_id)
        data["seen"] = seen[-5000:]
        self.save(data)

    def mark_published(self, item_id: str, message_id: int | None = None) -> None:
        data = self.load()
        data.setdefault("published", []).append({"item_id": item_id, "message_id": message_id})
        data["published"] = data["published"][-5000:]
        self.save(data)
