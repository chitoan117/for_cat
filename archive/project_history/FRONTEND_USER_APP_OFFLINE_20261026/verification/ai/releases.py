"""Session/source/image leakage checks and explicit dataset release metadata."""
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ai.artifacts import read_json, relative_file, write_json
from ai.dataset import ID_PATTERN, digest, image_integrity, load_manifest, validate_splits
from ai.sampling import fingerprint
from ai.session import SessionManifest


def leakage(root, rows, splits, *, near_limit=256, near_distance=3):
    if not 0 <= near_limit <= 1000 or not 0 <= near_distance <= 16:
        raise ValueError("invalid near-duplicate budget")
    failures = [{"code": "SESSION_LEAKAGE", "detail": e} for e in validate_splits(splits)]
    if failures and any("structure" in e["detail"] for e in failures):
        return {"failures": failures, "near_duplicates": [], "near_check_truncated": bool(rows)}
    memberships = defaultdict(set)
    for name in ("train", "validation", "test"):
        for session in splits[name]:
            memberships[session].add(name)
    for field, code in (("source_hash", "SOURCE_LEAKAGE"), ("hash", "EXACT_DUPLICATE_LEAKAGE")):
        groups = defaultdict(set)
        sessions = defaultdict(set)
        for row in rows:
            groups[row[field]].update(memberships[row["session_id"]])
            sessions[row[field]].add(row["session_id"])
        failures.extend({"code": code, "hash": sha, "splits": sorted(names), "sessions": sorted(sessions[sha])}
                        for sha, names in groups.items() if len(names) > 1)
    unknown = set(memberships)-{r["session_id"] for r in rows}
    if unknown:
        failures.append({"code": "SPLIT_SESSION_MISSING", "sessions": sorted(unknown)})
    fingerprints, warnings = [], []
    try:
        from PIL import Image
    except ImportError:
        return {"failures": failures, "near_duplicates": [], "near_check_truncated": bool(rows), "decoder": "UNAVAILABLE"}
    for row in sorted(rows, key=lambda r: r["sample_id"])[:near_limit]:
        try:
            path = relative_file(Path(root), row["path"])
            if image_integrity(path) != "OK":
                continue
            with Image.open(path) as image:
                value = fingerprint(image)
            current = memberships[row["session_id"]]
            for old, old_splits, old_id in fingerprints:
                if current and old_splits and current != old_splits and (value ^ old).bit_count() <= near_distance:
                    warnings.append({"code": "NEAR_DUPLICATE_REVIEW_REQUIRED", "samples": [old_id, row["sample_id"]]})
            fingerprints.append((value, current, row["sample_id"]))
        except (OSError, ValueError):
            continue
    return {"failures": failures, "near_duplicates": warnings, "near_check_truncated": len(rows) > near_limit,
            "near_checked": len(fingerprints), "decoder": "PILLOW"}


def acceptance(root, *, task="identity", stage="PILOT_DATASET", min_sessions=2,
               required_labels=None, near_limit=256):
    if stage not in ("PILOT_DATASET", "TRAINING_CANDIDATE", "TEST_CANDIDATE") or task not in ("identity", "behavior") or min_sessions < 2:
        raise ValueError("invalid acceptance policy")
    required = required_labels or (["OWNER_CAT", "OTHER_CAT", "OTHER_OBJECT"] if task=="identity" else ["EATING", "DRINKING", "OTHER"])
    allowed = {"OWNER_CAT","OTHER_CAT","OTHER_OBJECT"} if task=="identity" else {"EATING","DRINKING","OTHER"}
    if not isinstance(required,list) or not required or not set(required).issubset(allowed):
        raise ValueError("invalid required class coverage policy")
    rows, errors = load_manifest(Path(root))
    if not rows and not errors:
        return {"status": "DATASET_NOT_AVAILABLE", "samples": 0, "failures": [], "warnings": []}
    if len(rows) > 10000:
        return {"status": "REJECTED", "failures": ["FULL_VALIDATION_BUDGET_EXCEEDED"], "warnings": []}
    failures, warnings = list(errors), []
    for row in rows:
        try:
            path = relative_file(Path(root), row["path"])
            if image_integrity(path) != "OK" or digest(path) != row["hash"]:
                failures.append(f"SAMPLE_INTEGRITY:{row['sample_id']}")
        except (OSError, ValueError):
            failures.append(f"SAMPLE_PATH_OR_HASH:{row['sample_id']}")
    usable = [r for r in rows if r["usable"] and r[f"{task}_label"] in required]
    counts = Counter(r[f"{task}_label"] for r in usable)
    warnings.extend(f"CLASS_MISSING:{label}" for label in required if not counts[label])
    if len({r["session_id"] for r in usable}) < min_sessions:
        warnings.append("MULTIPLE_USABLE_SESSIONS_REQUIRED")
    for field in ("lighting", "view_angle"):
        if len({r.get(field) for r in usable if r.get(field)}) < 2:
            warnings.append(f"DIVERSITY_REVIEW:{field}")
    split_file = Path(root)/"splits.json"
    splits = read_json(split_file) if split_file.exists() else {"train": [], "validation": [], "test": []}
    if validate_splits(splits) and any("structure" in e for e in validate_splits(splits)):
        failures.append("INVALID_SPLIT_STRUCTURE")
        splits={"train":[],"validation":[],"test":[]}
    checked = leakage(root, rows, splits, near_limit=near_limit)
    failures.extend(checked["failures"])
    warnings.extend(checked["near_duplicates"])
    if checked["near_check_truncated"]:
        warnings.append("NEAR_DUPLICATE_CHECK_INCOMPLETE")
    if stage != "PILOT_DATASET":
        for name in ("train", "validation", "test"):
            labels = {r[f"{task}_label"] for r in usable if r["session_id"] in set(splits.get(name, []))}
            if not set(required).issubset(labels):
                failures.append(f"SPLIT_CLASS_COVERAGE:{name}")
        assigned = set().union(*(set(splits.get(name, [])) for name in ("train", "validation", "test")))
        if any(r["session_id"] not in assigned for r in usable):
            failures.append("UNASSIGNED_USABLE_SESSION")
        # Candidate approval fails closed pending coverage/diversity/near-duplicate review.
        failures.extend(warnings)
    return {"status": "REJECTED" if failures else stage, "task": task, "samples": len(rows),
            "usable_samples": len(usable), "usable_rate": len(usable)/len(rows) if rows else None,
            "session_count": len({r["session_id"] for r in rows}), "class_counts": dict(counts),
            "imbalance_ratio": max(counts.values())/min(counts.values()) if counts else None,
            "failures": failures, "warnings": warnings, "split_check": checked,
            "policy": {"required_labels": required, "min_sessions": min_sessions, "stage": stage}}


def create_release(root, version, output, *, apply=False, **policy):
    if not ID_PATTERN.fullmatch(version):
        raise ValueError("invalid dataset version")
    rows, _ = load_manifest(Path(root))
    checked = acceptance(root, **policy)
    splits_path = Path(root)/"splits.json"
    splits = read_json(splits_path) if splits_path.exists() else {"train": [], "validation": [], "test": []}
    if validate_splits(splits) and any("structure" in e for e in validate_splits(splits)):
        splits={"train":[],"validation":[],"test":[]}
    result = {"schema_version": 1, "dataset_version": version, "created_at": datetime.now(timezone.utc).isoformat(),
        "label_schema_version": 1, "session_count": len({r["session_id"] for r in rows}), "sample_count": len(rows),
        "split_counts": {name: sum(r["session_id"] in sessions for r in rows) for name, sessions in splits.items()},
        "class_counts": {task: dict(Counter(r[f"{task}_label"] or "MISSING" for r in rows)) for task in ("identity", "behavior")},
        "source_hashes": sorted({r["source_hash"] for r in rows}), "splits": splits,
        "manifest_hash": digest(Path(root)/"manifest.jsonl") if (Path(root)/"manifest.jsonl").exists() else None,
        "validation_status": checked["status"], "validation": checked}
    if apply:
        if checked["status"] in ("REJECTED", "DATASET_NOT_AVAILABLE"):
            raise ValueError("dataset release rejected: "+json.dumps(checked["failures"])[:512])
        write_json(Path(output)/f"{version}.json", result)
    return result


def ingest_sessions(sessions, destination, *, apply=False):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("ingest creates a new dataset directory; no overwrite")
    rows, metas, seen = [], [], set()
    if not 1 <= len(sessions) <= 100:
        raise ValueError("supply 1..100 explicit session folders")
    for folder in map(Path, sessions):
        meta = SessionManifest.model_validate(read_json(folder/"session.json"))
        if meta.session_id in {m.session_id for m in metas}:
            raise ValueError("duplicate session")
        samples, errors = load_manifest(folder)
        if errors or not samples or len(samples) != meta.sample_count:
            raise ValueError("invalid/empty session samples")
        for row in samples:
            source = relative_file(folder, row["path"])
            if row["session_id"] != meta.session_id or row["source_hash"] != meta.source_hash or image_integrity(source)!="OK" or digest(source)!=row["hash"]:
                raise ValueError("session/image provenance mismatch")
            if row["sample_id"] in seen:
                raise ValueError("duplicate sample across sessions")
            seen.add(row["sample_id"])
            # Distinct source subfolders may contain the same basename; never overwrite.
            rows.append((source, {**row, "path": f"processed/{meta.session_id}/{row['sample_id']}{source.suffix.lower()}"}))
        metas.append(meta)
    if apply:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".ingest-", dir=destination.parent))
        try:
            for source, row in rows:
                target = stage/row["path"]; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
            (stage/"manifest.jsonl").write_text("".join(json.dumps(row)+"\n" for _, row in rows), encoding="utf-8")
            for meta in metas:
                write_json(stage/"sessions"/f"{meta.session_id}.json", meta.model_dump(mode="json"))
            if destination.exists():
                raise FileExistsError("destination already exists")
            stage.rename(destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return {"status": "INGESTED" if apply else "DRY_RUN", "sessions": len(metas), "samples": len(rows)}
