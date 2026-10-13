"""Bounded, deterministic, session-aware metadata operations; no downloads."""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ai.artifacts import relative_file, parse_json

ROOT = Path(__file__).resolve().parent / "datasets"
IDENTITY_LABELS = {"OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT", "UNKNOWN", "SKIP", None}
BEHAVIOR_LABELS = {"EATING", "DRINKING", "NEAR_FOOD", "NEAR_WATER", "LEAVING", "OTHER", "UNSURE", "SKIP", None}
OPTIONAL = ("food_type", "lighting", "distance", "view_angle", "occlusion", "camera_device", "notes")
REQUIRED = ("sample_id", "session_id", "source_video", "timestamp", "identity_label",
            "behavior_label", "usable", "hash", "source_hash", "path")
ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,64}$")


def digest(path: Path) -> str:
    if not path.is_file() or path.stat().st_size > 1_000_000_000:
        raise ValueError("source missing or exceeds 1 GB cap")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def validate_row(row: dict) -> List[str]:
    errors = []
    if not isinstance(row, dict):
        return ["metadata row must be an object"]
    errors += [f"missing {key}" for key in REQUIRED if key not in row]
    errors += [f"unknown field {key}" for key in row if key not in REQUIRED + OPTIONAL + ("source_offset_seconds",)]
    for key in ("sample_id", "session_id"):
        if key in row and (not isinstance(row[key], str) or not ID_PATTERN.fullmatch(row[key])):
            errors.append(f"invalid {key}")
    if not (row.get("identity_label") is None or
            isinstance(row.get("identity_label"), str) and row["identity_label"] in IDENTITY_LABELS):
        errors.append("invalid identity_label")
    if not (row.get("behavior_label") is None or
            isinstance(row.get("behavior_label"), str) and row["behavior_label"] in BEHAVIOR_LABELS):
        errors.append("invalid behavior_label")
    if "usable" in row and not isinstance(row["usable"], bool):
        errors.append("usable must be boolean")
    for key in ("hash", "source_hash"):
        if key in row and (not isinstance(row[key], str) or not re.fullmatch(r"[a-f0-9]{64}", row[key])):
            errors.append(f"invalid {key}")
    for key, limit in (("source_video", 128), ("path", 128), *( (name, 256 if name == "notes" else 64) for name in OPTIONAL)):
        value = row.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            errors.append(f"invalid {key}")
    if isinstance(row.get("path"), str) and row["path"]:
        path = Path(row["path"])
        if path.anchor or ".." in path.parts or "\\" in row["path"] or ":" in row["path"]:
            errors.append("invalid relative path")
    else:
        errors.append("path must be a nonempty relative filename")
    if isinstance(row.get("source_video"), str) and row["source_video"]:
        if Path(row["source_video"]).name != row["source_video"]:
            errors.append("source_video must be a basename")
    if row.get("timestamp") is not None:
        try:
            date = datetime.fromisoformat(row["timestamp"])
            if date.tzinfo is None or date.utcoffset() is None:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append("timestamp must be timezone-aware ISO 8601 or null")
    offset = row.get("source_offset_seconds")
    if offset is not None and (not isinstance(offset, (float, int)) or not 0 <= offset <= 1_000_000):
        errors.append("invalid video offset")
    return errors


def load_manifest(root: Path = ROOT) -> Tuple[List[dict], List[str]]:
    manifest = root / "manifest.jsonl"
    if not manifest.exists():
        return [], []
    if not manifest.is_file():
        return [], ["manifest is not a file"]
    if manifest.stat().st_size > 20_000_000:
        return [], ["manifest exceeds 20 MB limit"]
    rows, errors = [], []
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except UnicodeError:
        return [], ["manifest is not UTF-8"]
    for line_no, line in enumerate(lines, 1):
        try:
            row = parse_json(line)
        except (ValueError, UnicodeError, RecursionError):
            errors.append(f"line {line_no}: invalid JSON")
            continue
        problems = validate_row(row)
        errors.extend(f"line {line_no}: {problem}" for problem in problems)
        if not problems:
            rows.append(row)
    if len({r["sample_id"] for r in rows}) != len(rows):
        errors.append("duplicate sample_id")
    return rows, errors


def append_row(root: Path, row: dict, *, apply: bool = False) -> dict:
    problems = validate_row(row)
    if problems:
        raise ValueError("; ".join(problems))
    old, errors = load_manifest(root)
    if errors:
        raise ValueError("invalid existing manifest: " + "; ".join(errors[:3]))
    if row["sample_id"] in {r["sample_id"] for r in old} or row["hash"] in {r["hash"] for r in old}:
        raise ValueError("duplicate sample ID or exact image hash")
    if apply:
        root.mkdir(parents=True, exist_ok=True)
        with (root / "manifest.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    return {"status": "IMPORTED" if apply else "DRY_RUN", "sample_id": row["sample_id"]}


def split_sessions(rows: List[dict], seed: int = 42) -> Dict[str, List[str]]:
    sessions = sorted({r["session_id"] for r in rows if r.get("usable") and
                       r.get("identity_label") not in (None, "SKIP")},
                      key=lambda x: hashlib.sha256(f"{seed}:{x}".encode()).hexdigest())
    total = len(sessions)
    if total < 3:
        return {"train": sessions, "validation": [], "test": []}
    train = max(1, int(total * 0.7))
    validation = max(1, int(total * 0.15))
    if train + validation >= total:
        train = total - 2
        validation = 1
    return {"train": sessions[:train], "validation": sessions[train:train + validation],
            "test": sessions[train + validation:]}


def validate_splits(splits: Dict[str, List[str]]) -> List[str]:
    if not isinstance(splits, dict) or any(not isinstance(splits.get(name), list)
                                           or any(not isinstance(value, str) for value in splits[name])
                                           for name in ("train", "validation", "test")):
        return ["invalid session split structure"]
    sets = [set(splits.get(name, [])) for name in ("train", "validation", "test")]
    return ["session leakage across splits"] if any(sets[i] & sets[j]
        for i, j in ((0, 1), (0, 2), (1, 2))) else []


def image_integrity(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    if path.stat().st_size > 8_000_000:
        return "CORRUPT"
    try:
        from PIL import Image
    except ImportError:
        return "DECODER_UNAVAILABLE"
    try:
        with Image.open(path) as image:
            image.verify()
        return "OK"
    except Exception:  # Pillow may raise a decompression-bomb exception
        return "CORRUPT"


def near_duplicate_warnings(root: Path, rows: List[dict], max_checked: int = 256) -> Optional[int]:
    """Small perceptual hash warning; never a substitute for human review."""
    try:
        from PIL import Image
    except ImportError:
        return None
    fingerprints = []
    for row in rows[:max_checked]:
        try:
            path = relative_file(root,row["path"])
            with Image.open(path) as image:
                gray = image.convert("L").resize((9, 8))
                pixels = list(gray.tobytes())
            bits = sum((pixels[y * 9 + x] > pixels[y * 9 + x + 1]) << (y * 8 + x)
                       for y in range(8) for x in range(8))
            fingerprints.append(bits)
        except Exception:
            continue
    return sum((fingerprints[i] ^ fingerprints[j]).bit_count() <= 3
               for i in range(len(fingerprints)) for j in range(i + 1, len(fingerprints)))


def report(root: Path = ROOT) -> dict:
    rows, errors = load_manifest(root)
    if not rows and not errors:
        return {"status": "DATASET_NOT_AVAILABLE", "samples": 0}
    split_path = root / "splits.json"
    splits = None
    if split_path.is_file():
        try:
            splits = json.loads(split_path.read_text(encoding="utf-8"))
            if not isinstance(splits, dict) or any(not isinstance(splits.get(name), list)
                                                  for name in ("train", "validation", "test")):
                raise ValueError("invalid splits structure")
            errors.extend(validate_splits(splits))
        except (ValueError, UnicodeError):
            errors.append("invalid splits JSON")
    counts = Counter(row["hash"] for row in rows)
    paths = {}
    for row in rows:
        try:
            paths[row["sample_id"]] = relative_file(root,row["path"])
        except ValueError:
            errors.append(f"unsafe image path: {row['sample_id']}")
    quality = Counter(image_integrity(paths[row["sample_id"]]) if row["sample_id"] in paths else "CORRUPT" for row in rows)
    hash_mismatches = 0
    for row in rows[:1000]:  # bounded integrity work per report
        path = paths.get(row["sample_id"])
        if path is None:
            continue
        if path.is_file():
            try:
                if digest(path) != row["hash"]:
                    hash_mismatches += 1
            except ValueError:
                errors.append(f"oversized image: {row['sample_id']}")
    identity = Counter(r["identity_label"] or "MISSING" for r in rows)
    behavior = Counter(r["behavior_label"] or "MISSING" for r in rows)
    unavailable = any(quality.get(name, 0) for name in ("MISSING", "CORRUPT", "DECODER_UNAVAILABLE"))
    split_leakage = None
    if splits is not None:
        from ai.releases import leakage
        split_leakage = leakage(root,rows,splits)
        errors.extend(f"{entry['code']}: {entry.get('detail',entry.get('hash',''))}" for entry in split_leakage["failures"])
    return {
        "status": "DATASET_INVALID" if errors or unavailable or hash_mismatches else "DATASET_AVAILABLE",
        "samples": len(rows), "identity": dict(identity),
        "behavior": dict(behavior),
        "sessions": dict(Counter(r["session_id"] for r in rows)),
        "lighting": dict(Counter(r.get("lighting") or "UNKNOWN" for r in rows)),
        "distance": dict(Counter(r.get("distance") or "UNKNOWN" for r in rows)),
        "view_angle": dict(Counter(r.get("view_angle") or "UNKNOWN" for r in rows)),
        "occlusion": dict(Counter(r.get("occlusion") or "UNKNOWN" for r in rows)),
        "food_types": dict(Counter(r.get("food_type") or "UNKNOWN" for r in rows)),
        "exact_duplicate_hashes": sum(n - 1 for n in counts.values() if n > 1),
        "near_duplicate_warnings_first_256": near_duplicate_warnings(root, rows),
        "hash_mismatches_first_1000": hash_mismatches,
        "class_imbalance_warning": any(max(class_counts.values(), default=0) > len(rows) * 0.8
                                       for class_counts in (identity, behavior)),
        "coverage_gaps": [name for name, values in (("lighting", "lighting"),
                          ("distance", "distance"), ("view_angle", "view_angle"),
                          ("occlusion", "occlusion"), ("food_type", "food_type"))
                          if all(not r.get(values) for r in rows)],
        "image_integrity": dict(quality),
        "missing_labels": sum(r["identity_label"] is None or r["behavior_label"] is None for r in rows),
        "unusable": sum(not r["usable"] for r in rows),
        "splits": splits, "errors": errors,"split_leakage":split_leakage,
    }
