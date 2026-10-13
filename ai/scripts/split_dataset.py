"""Session-level deterministic split: never mix nearby video frames across sets."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, load_manifest, split_sessions, validate_splits


def split(root: Path, seed: int = 42, *, apply: bool = False) -> dict:
    rows, errors = load_manifest(root)
    if errors:
        raise ValueError("invalid manifest: " + "; ".join(errors[:3]))
    if not rows:
        return {"status": "DATASET_NOT_AVAILABLE", "splits": {"train": [], "validation": [], "test": []}}
    groups = split_sessions(rows, seed)
    if validate_splits(groups):
        raise ValueError("session leakage")
    output = {"status": "SPLIT" if apply else "DRY_RUN", "seed": seed, "splits": groups}
    if apply:
        with (root / "splits.json").open("x", encoding="utf-8") as stream:
            json.dump(groups, stream, sort_keys=True, indent=2)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(split(args.dataset, args.seed, apply=args.apply), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"SPLIT_FAILED: {exc}\n")
