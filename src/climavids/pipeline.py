from __future__ import annotations

import json
from pathlib import Path

from climavids.collectors.gdelt import collect as collect_gdelt
from climavids.collectors.rss import collect as collect_rss
from climavids.content import render
from climavids.dedup import similarity
from climavids.models import Source
from climavids.scoring import score
from climavids.state import JsonState


def load_sources(path: str = "data/sources.json") -> list[Source]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Source.model_validate(x) for x in data if x.get("enabled", True)]


def run(*, dry_run: bool = True, limit: int = 8) -> list[dict]:
    state = JsonState()
    raw = []
    for source in load_sources():
        try:
            if source.kind == "gdelt":
                raw.extend(collect_gdelt(source, limit=50))
            elif source.kind == "rss":
                raw.extend(collect_rss(source, limit=50))
        except Exception as exc:
            print(f"SOURCE_ERROR {source.id}: {type(exc).__name__}")

    unique = []
    for item in raw:
        # Do not discard an item just because a previous run examined it if it
        # has never actually been published. This makes failed sends retryable.
        if state.published(item.id):
            continue
        if any(similarity(item.title, old.title) >= 0.72 for old in unique):
            continue
        unique.append(item)

    ranked = sorted((score(x) for x in unique), key=lambda x: x.total, reverse=True)
    selected = [x for x in ranked if x.total >= 62][:limit]
    output = []
    for i, scored in enumerate(selected):
        draft = render(scored.item, ["news", "short", "question", "analysis"][i % 4])
        output.append({"score": scored.total, "draft": draft.model_dump(mode="json")})

    if output:
        Path("data/dry_run.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        # Dry-run never mutates durable publication state.
        if not dry_run:
            for item in selected:
                state.mark_seen(item.item.id)

    return output
