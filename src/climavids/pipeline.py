from __future__ import annotations

import json
from pathlib import Path

from climavids.collectors.gdelt import collect as collect_gdelt
from climavids.collectors.rss import collect as collect_rss
from climavids.collectors.telegram_web import collect as collect_telegram
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
    source_counts: dict[str, int] = {}

    for source in load_sources():
        before = len(raw)
        try:
            if source.kind == "gdelt":
                raw.extend(collect_gdelt(source, limit=50))
            elif source.kind == "rss":
                raw.extend(collect_rss(source, limit=50))
            elif source.kind == "telegram_web":
                raw.extend(collect_telegram(source, limit=30))
            source_counts[source.id] = len(raw) - before
        except Exception as exc:
            source_counts[source.id] = 0
            print(f"SOURCE_ERROR {source.id}: {type(exc).__name__}: {exc}")

    unique = []
    for item in raw:
        if state.published(item.id):
            continue
        if any(similarity(item.title, old.title) >= 0.72 for old in unique):
            continue
        unique.append(item)

    ranked = sorted((score(x) for x in unique), key=lambda x: x.total, reverse=True)
    selected = [x for x in ranked if x.total >= 62][:limit]

    print(
        "PIPELINE_SUMMARY "
        f"sources={source_counts} raw={len(raw)} unique={len(unique)} "
        f"ranked={len(ranked)} selected={len(selected)}"
    )
    if ranked:
        top = ranked[:5]
        print(
            "TOP_CANDIDATES "
            + " | ".join(
                f"{x.item.source_id}:{x.total}:{x.item.title[:90]}" for x in top
            )
        )

    output = []
    for i, scored in enumerate(selected):
        draft = render(scored.item, ["news", "short", "question", "analysis"][i % 4])
        output.append({"score": scored.total, "draft": draft.model_dump(mode="json")})

    if dry_run and output:
        Path("data/dry_run.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return output
