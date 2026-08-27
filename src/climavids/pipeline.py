from __future__ import annotations

import json
from datetime import datetime, timezone
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
    """Collect broadly, filter duplicates conservatively, and always keep a publishable fallback."""
    state = JsonState()
    raw = []
    source_counts: dict[str, int] = {}
    source_errors: list[str] = []
    sources = load_sources()

    print(f"PIPELINE_START dry_run={dry_run} enabled_sources={len(sources)} limit={limit}")

    for source in sources:
        before = len(raw)
        try:
            if source.kind == "gdelt":
                raw.extend(collect_gdelt(source, limit=50))
            elif source.kind == "rss":
                raw.extend(collect_rss(source, limit=50))
            elif source.kind == "telegram_web":
                raw.extend(collect_telegram(source, limit=30))
            source_counts[source.id] = len(raw) - before
            print(f"SOURCE_OK id={source.id} kind={source.kind} items={source_counts[source.id]}")
        except Exception as exc:
            source_counts[source.id] = 0
            error = f"{source.id}: {type(exc).__name__}: {exc}"
            source_errors.append(error)
            print(f"SOURCE_ERROR {error}")

    unique = []
    for item in raw:
        if state.published(item.id):
            continue
        # Conservative title deduplication: only suppress near-identical titles.
        if any(similarity(item.title, old.title) >= 0.82 for old in unique):
            continue
        unique.append(item)

    ranked = sorted((score(x) for x in unique), key=lambda x: x.total, reverse=True)

    # Do not let a hard quality threshold block publication completely.
    # Prefer strong candidates, but if none reaches the preference floor,
    # publish the best available non-duplicate item instead of producing nothing.
    preferred = [x for x in ranked if x.total >= 50]
    selected = (preferred or ranked)[:limit]

    print(
        "PIPELINE_SUMMARY "
        f"raw={len(raw)} unique={len(unique)} ranked={len(ranked)} "
        f"preferred={len(preferred)} selected={len(selected)} source_errors={len(source_errors)}"
    )
    if ranked:
        print(
            "TOP_CANDIDATES "
            + " | ".join(
                f"{x.item.source_id}:{x.total}:{x.item.title[:90]}" for x in ranked[:5]
            )
        )

    output = []
    for i, scored in enumerate(selected):
        draft = render(scored.item, ["news", "short", "question", "analysis"][i % 4])
        output.append({"score": scored.total, "draft": draft.model_dump(mode="json")})

    data = state.load()
    metrics = data.setdefault("metrics", {})
    metrics.update(
        {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "last_result": "dry-run" if dry_run else "pipeline-complete",
            "last_sources": len(sources),
            "last_source_counts": source_counts,
            "last_source_errors": len(source_errors),
            "last_raw_items": len(raw),
            "last_unique_items": len(unique),
            "last_candidates": len(ranked),
            "last_preferred": len(preferred),
            "last_selected": len(output),
            "errors": (metrics.get("errors", []) + source_errors)[-20:],
        }
    )
    state.save(data)

    print(f"PIPELINE_END selected={len(output)}")

    if dry_run and output:
        Path("data/dry_run.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return output
