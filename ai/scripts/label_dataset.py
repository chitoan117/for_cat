"""Resumable non-interactive labeling; explicit --apply, no silent overwrite."""

import argparse
import json
import os
import tempfile
from pathlib import Path

from ai.dataset import ROOT, BEHAVIOR_LABELS, IDENTITY_LABELS, load_manifest


def label(root: Path, sample_id: str, identity: str, behavior: str,
          *, usable: bool = True, apply: bool = False) -> dict:
    if identity not in IDENTITY_LABELS or behavior not in BEHAVIOR_LABELS:
        raise ValueError("invalid identity or behavior label")
    rows, errors = load_manifest(root)
    if errors:
        raise ValueError("invalid metadata: " + "; ".join(errors[:3]))
    matches = [r for r in rows if r["sample_id"] == sample_id]
    if not matches:
        raise ValueError("sample ID not found")
    old = matches[0]
    if old["identity_label"] is not None or old["behavior_label"] is not None:
        raise ValueError("already labeled; no silent overwrite")
    old["identity_label"] = identity
    old["behavior_label"] = behavior
    old["usable"] = usable and identity != "SKIP" and behavior != "SKIP"
    if apply:
        # Atomic replacement of metadata only after an explicit --apply.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root,
                                             prefix="manifest-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                for row in rows:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
            os.replace(temporary, root / "manifest.jsonl")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {"status": "LABELED" if apply else "DRY_RUN", "sample_id": sample_id,
            "identity_label": identity, "behavior_label": behavior, "usable": old["usable"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_id")
    parser.add_argument("--identity", required=True, choices=sorted(x for x in IDENTITY_LABELS if x))
    parser.add_argument("--behavior", required=True, choices=sorted(x for x in BEHAVIOR_LABELS if x))
    parser.add_argument("--unusable", action="store_true")
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(label(args.dataset, args.sample_id, args.identity, args.behavior,
                               usable=not args.unusable, apply=args.apply)))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"LABEL_FAILED: {exc}\n")
