from pathlib import Path
from climavids.utils import read_json, write_json, utc_now


class JsonState:
    def __init__(self, root: str = "data"):
        self.root = Path(root)

    def get_published(self) -> dict:
        return read_json(self.root / "published.json", {"items": {}})

    def is_published(self, content_id: str) -> bool:
        return content_id in self.get_published().get("items", {})

    def mark_published(self, content_id: str, message_id: int | None = None) -> None:
        state = self.get_published()
        state.setdefault("items", {})[content_id] = {
            "message_id": message_id,
            "published_at": utc_now(),
        }
        write_json(self.root / "published.json", state)
