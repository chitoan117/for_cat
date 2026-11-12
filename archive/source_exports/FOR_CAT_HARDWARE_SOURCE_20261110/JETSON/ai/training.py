"""Data-gated training plan only; no framework dependency or fake metrics."""

import json
from pathlib import Path

from ai.dataset import ROOT, load_manifest, report, validate_splits
from ai.label_schema import BEHAVIOR_V2, task_label

LABEL_MAPS = {
    "identity": ["OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT"],
    "behavior": ["EATING", "DRINKING", "OTHER"],
    "behavior_v2": list(BEHAVIOR_V2),
}


def prepare(task: str, root: Path = ROOT, seed: int = 42, patience: int = 5, *, near_review=None) -> dict:
    if task not in LABEL_MAPS or patience < 1:
        raise ValueError("invalid task or early-stopping patience")
    rows, errors = load_manifest(root)
    if errors:
        return {"status": "DATASET_INVALID", "errors": errors[:10]}
    if not rows:
        return {"status": "DATASET_NOT_AVAILABLE"}
    quality = report(root)
    if quality["status"] != "DATASET_AVAILABLE":
        return {"status": "DATASET_INVALID", "errors": quality.get("errors", []),
                "image_integrity": quality.get("image_integrity", {})}
    split_path = root / "splits.json"
    if not split_path.is_file():
        return {"status": "SPLITS_NOT_AVAILABLE"}
    try:
        splits = json.loads(split_path.read_text(encoding="utf-8"))
        errors = validate_splits(splits)
        if errors:
            return {"status": "SPLITS_INVALID", "errors": errors}
        groups = {name: [r for r in rows if r["session_id"] in set(splits[name]) and r["usable"]
                         and task_label(r, task) in LABEL_MAPS[task]]
                  for name in ("train", "validation", "test")}
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        return {"status": "SPLITS_INVALID", "errors": [str(exc)[:128]]}
    if not all(groups.values()):
        return {"status": "INSUFFICIENT_SESSION_SPLITS",
                "counts": {name: len(group) for name, group in groups.items()}}
    if task == "behavior_v2":
        from ai.releases import acceptance
        checked = acceptance(root, task=task, stage="TRAINING_CANDIDATE", near_limit=1000, near_review=near_review)
        if checked["status"] != "TRAINING_CANDIDATE":
            return {"status": "DATASET_NOT_READY_FOR_TRAINING", "label_map": LABEL_MAPS[task],
                    "validation": checked, "metrics": None, "model_metadata": None}
    return {"status": "READY_FOR_FUTURE_TRAINER", "task": task, "seed": seed,
            "label_map": LABEL_MAPS[task], "early_stopping_patience": patience,
            "train_sessions": sorted(splits["train"]),
            "validation_sessions": sorted(splits["validation"]),
            "test_sessions": sorted(splits["test"]),
            "counts": {name: len(group) for name, group in groups.items()},
            "metrics": None, "model_metadata": None,
            "test_set_usage": "evaluation only; never used for training/early stopping"}
