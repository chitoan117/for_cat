"""Session-level deterministic split: never mix nearby video frames across sets."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, load_manifest, split_sessions, validate_splits
from ai.artifacts import read_json
from ai.manifest_io import atomic_text, dataset_lock


def split(root: Path, seed: int = 42, *, apply: bool = False, refresh: bool = False) -> dict:
    with dataset_lock(root, apply):
        return _split(Path(root), seed, apply=apply, refresh=refresh)


def _split(root, seed, *, apply, refresh):
    rows, errors = load_manifest(root)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors[:3]))
    if not rows:
        return {"status": "DATASET_NOT_AVAILABLE", "splits": {"train": [], "validation": [], "test": []}}
    groups = split_sessions(rows, seed)
    v2 = any(row.get("schema_version") == 2 for row in rows)
    if v2:
        from ai.session_groups import source_groups
        independent = source_groups(rows)
        if len(independent) < 3:
            return {"status": "NOT_READY", "failures": ["AT_LEAST_3_INDEPENDENT_SOURCE_GROUPS_REQUIRED"], "independent_groups": len(independent)}
        assignment = split_sessions([], seed, source_sessions=list(independent))
        groups = {name: sorted(member for group in values for member in independent[group]) for name, values in assignment.items()}
    if validate_splits(groups):
        raise ValueError("session leakage")
    output = {"status": "SPLIT" if apply else "DRY_RUN", "seed": seed, "splits": groups}
    if apply:
        path = root / "splits.json"
        if path.exists():
            old = read_json(path)
            if v2 and old == groups:
                return {**output, "status": "UNCHANGED"}
            if not refresh:
                raise FileExistsError("split exists; explicit --refresh required; original not overwritten")
            from datetime import datetime, timezone
            import uuid
            backup = root / "split_history" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + uuid.uuid4().hex[:8] + ".json")
            backup.parent.mkdir(parents=True, exist_ok=True)
            with backup.open("xb") as stream:
                stream.write(path.read_bytes())
        atomic_text(path, json.dumps(groups, sort_keys=True, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="explicit resplit with immutable old-split backup")
    args = parser.parse_args()
    try:
        result = split(args.dataset, args.seed, apply=args.apply, refresh=args.refresh)
        print(json.dumps(result, indent=2))
        if result["status"] == "NOT_READY":
            parser.exit(2)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"SPLIT_FAILED: {exc}\n")
