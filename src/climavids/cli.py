import argparse
import json
from pathlib import Path

from climavids.collectors.rss import collect_rss
from climavids.dedup import deduplicate
from climavids.models import Source
from climavids.scoring import score
from climavids.state import JsonState


def load_sources(path: str = "data/sources.json") -> list[Source]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Source.model_validate(x) for x in data.get("sources", []) if x.get("enabled", True)]


def collect_command() -> int:
    all_items = []
    for source in load_sources():
        try:
            all_items.extend(collect_rss(source))
        except Exception as exc:
            print(f"SOURCE_ERROR {source.id}: {type(exc).__name__}")
    unique = deduplicate(all_items)
    scored = sorted((score(x) for x in unique), key=lambda x: x.total, reverse=True)
    for candidate in scored[:10]:
        print(json.dumps({"id": candidate.item.id, "title": candidate.item.title, "score": candidate.total, "status": candidate.status}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["collect", "health"])
    args = parser.parse_args()
    if args.command == "collect":
        return collect_command()
    state = JsonState()
    print(json.dumps({"ok": True, "published_count": len(state.get_published().get("items", {}))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
