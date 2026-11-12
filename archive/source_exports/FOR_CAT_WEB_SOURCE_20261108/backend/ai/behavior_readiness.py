"""Full offline video-dataset readiness and immutable JSON/Markdown reports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from ai.artifacts import read_json, relative_file
from ai.dataset import digest, image_integrity, load_manifest
from ai.label_schema import BEHAVIOR_V2, task_label
from ai.quality import image_quality, near_pairs
from ai.releases import leakage
from ai.scripts.import_video import VIDEO_BYTE_CAP, load_sources
from ai.session_groups import source_groups

STATES = BEHAVIOR_V2 + ("NONE", "UNKNOWN", "UNSURE", "UNANNOTATED", "SKIP")


def readiness(root, *, min_class_samples=10, blur_threshold=50, near_comparison_limit=2_000_000,
              near_review=None):
    root = Path(root)
    def snapshot():
        return {name: digest(root / name) if (root / name).is_file() else None
                for name in ("manifest.jsonl", "sources.jsonl", "splits.json")}
    initial_snapshot = snapshot()
    if type(min_class_samples) is not int or min_class_samples < 3:
        raise ValueError("minimum class coverage must be >=3, not a one-frame training claim")
    failures, warnings = [], []
    rows, errors = load_manifest(root)
    failures.extend(errors)
    try:
        sources = load_sources(root)
    except (ValueError, OSError) as error:
        sources = []
        failures.append("SOURCE_CATALOG_INVALID:" + str(error))
    manifest_hash = initial_snapshot["manifest.jsonl"]
    source_map = {source["session_id"]: source for source in sources}
    if not sources:
        failures.append("SOURCE_VIDEOS_MISSING")
    if not rows:
        failures.append("EXTRACTED_SAMPLES_MISSING")
    if any(row.get("schema_version") != 2 for row in rows):
        failures.append("USE_A_SEPARATE_SCHEMA_V2_DATASET")
    group_rows = rows + [{"session_id": source["session_id"], "source_hash": source["source_hash"],
                          **source.get("session_metadata", {})} for source in sources]
    independent = source_groups(group_rows)
    if len(independent) < 3:
        failures.append("AT_LEAST_3_INDEPENDENT_SOURCE_GROUPS_REQUIRED")
    splits = {"train": [], "validation": [], "test": []}
    if (root / "splits.json").exists():
        try:
            splits = read_json(root / "splits.json")
        except (ValueError, OSError) as error:
            failures.append("SPLITS_INVALID:" + str(error))
    else:
        failures.append("SESSION_SPLIT_MISSING")
    structural = leakage(root, rows, splits, near_limit=0)
    failures.extend(item["code"] for item in structural["failures"])
    if any("structure" in str(item) for item in structural["failures"]):
        splits = {"train": [], "validation": [], "test": []}
    memberships = defaultdict(set)
    for name in ("train", "validation", "test"):
        for session in splits.get(name, []):
            memberships[session].add(name)
    for source in sources:
        if len(memberships[source["session_id"]]) != 1:
            failures.append("SOURCE_SESSION_UNASSIGNED_OR_MULTIPLY_ASSIGNED:" + source["session_id"])
    labels, coverage, usable_labels = Counter(), Counter(), Counter()
    sessions = defaultdict(list)
    extractions = {}
    for identifier in set(source_map) | {row["session_id"] for row in rows}:
        path = root / "extractions" / (identifier + ".json")
        try:
            extractions[identifier] = read_json(path) if path.is_file() else {}
        except (ValueError, OSError):
            extractions[identifier] = {}
            failures.append("EXTRACTION_RECEIPT_INVALID:" + identifier)
    fingerprints = []
    corrupt = blur = missing_sequence = quality_unavailable = hash_mismatch = 0
    for row in rows:
        sessions[row["session_id"]].append(row)
        state = row["behavior_label"] or "UNANNOTATED"
        labels[state] += 1
        trainable = row["usable"] and task_label(row, "behavior_v2") in BEHAVIOR_V2
        if trainable:
            usable_labels[state] += 1
        source = source_map.get(row["session_id"])
        if source is None or source["source_hash"] != row["source_hash"] or source["source_video"] != row["source_video"]:
            failures.append("SAMPLE_SOURCE_PROVENANCE_MISMATCH:" + row["sample_id"])
        if source and any(row.get(key) != value for key, value in source.get("session_metadata", {}).items()):
            failures.append("SAMPLE_SESSION_METADATA_MISMATCH:" + row["sample_id"])
        if row.get("frame_index") is None or row.get("sample_sequence") is None or row.get("source_offset_seconds") is None:
            missing_sequence += 1
        step = 0.5
        step = extractions.get(row["session_id"], {}).get("settings", {}).get("interval_seconds") or step
        offset = row.get("source_offset_seconds")
        duration = (source or {}).get("media", {}).get("duration_seconds")
        if offset is not None:
            coverage[state] += max(0, min(step, duration-offset)) if duration is not None else step
        try:
            path = relative_file(root, row["path"])
            if image_integrity(path) != "OK":
                corrupt += 1
                continue
            if digest(path) != row["hash"]:
                hash_mismatch += 1
            from PIL import Image
            with Image.open(path) as image:
                metrics = image_quality(image, blur_threshold)
            blur += int(metrics["blur_warning"])
            names = memberships[row["session_id"]]
            fingerprints.append({"sample_id": row["sample_id"], "source_hash": row["source_hash"],
                                 "dhash": metrics["dhash"], "split": next(iter(names)) if len(names) == 1 and trainable else None})
        except ImportError:
            quality_unavailable += 1
        except (ValueError, OSError):
            corrupt += 1
    near = near_pairs(fingerprints, comparison_limit=near_comparison_limit)
    reviewed = False
    if near_review:
        document = read_json(Path(near_review))
        expected_pairs = {tuple(pair) for pair in near["cross_source_pairs"]}
        actual_pairs = document.get("reviewed_source_pairs", [])
        if not isinstance(actual_pairs, list) or any(not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(value, str) for value in pair) for pair in actual_pairs):
            raise ValueError("invalid reviewed source-pair list")
        reviewed = (document.get("review_source") == "HUMAN_REVIEWED_SOURCE_SESSIONS"
                    and document.get("manifest_sha256") == manifest_hash
                    and {tuple(sorted(pair)) for pair in actual_pairs} >= expected_pairs
                    and isinstance(document.get("notes"), str) and bool(document["notes"].strip()))
        if not reviewed:
            failures.append("NEAR_REVIEW_DOCUMENT_INVALID_OR_STALE")
    if not near["complete"]:
        failures.append("FULL_NEAR_CHECK_BUDGET_EXCEEDED")
    if near["cross_split_pairs"] and not reviewed:
        failures.append("CROSS_SPLIT_NEAR_DUPLICATE_HUMAN_REVIEW_REQUIRED")
    if near["pairs"]:
        warnings.append("NEAR_DUPLICATE_WARNINGS_ARE_SIMILARITY_NOT_PROVEN_LEAKAGE")
    if corrupt or hash_mismatch:
        failures.append("CORRUPT_MISSING_OR_CHANGED_SAMPLES")
    if quality_unavailable:
        failures.append("QUALITY_DECODER_UNAVAILABLE")
    if missing_sequence:
        failures.append("SAMPLE_SEQUENCE_OR_SOURCE_TIMESTAMP_MISSING")
    if blur:
        warnings.append("BLUR_FLAGS_REQUIRE_REVIEW_NOT_AUTOMATIC_DELETION")
    known_duration = 0.0
    per_session = []
    extraction_totals = Counter()
    for source in sources:
        identifier = source["session_id"]
        samples = sessions.get(identifier, [])
        media = source.get("media", {})
        ordered = sorted(samples, key=lambda row: row.get("frame_index", -1))
        for left, right in zip(ordered, ordered[1:]):
            if (left.get("frame_index", -1) >= right.get("frame_index", -1) or
                left.get("sample_sequence", -1) >= right.get("sample_sequence", -1) or
                (left.get("source_offset_seconds") is not None and right.get("source_offset_seconds") is not None and
                 left["source_offset_seconds"] >= right["source_offset_seconds"])):
                failures.append("SOURCE_SAMPLE_ORDER_OR_POSITION_INVALID:" + identifier)
        if not samples:
            failures.append("SESSION_WITHOUT_RETAINED_SAMPLES:" + identifier)
        for key in ("original_filename", "import_timestamp", "media"):
            if not source.get(key):
                warnings.append("SOURCE_METADATA_MISSING:" + identifier + ":" + key)
        if not media.get("readable") or media.get("duration_seconds") is None or not media.get("fps"):
            failures.append("SOURCE_MEDIA_METADATA_UNREADABLE:" + identifier)
        else:
            known_duration += media["duration_seconds"]
        try:
            if digest(relative_file(root / "raw", source["source_video"]), max_bytes=VIDEO_BYTE_CAP) != source["source_hash"]:
                failures.append("SOURCE_VIDEO_HASH_MISMATCH:" + identifier)
        except (ValueError, OSError):
            failures.append("SOURCE_VIDEO_MISSING_OR_UNREADABLE:" + identifier)
        extraction = extractions[identifier]
        if not extraction:
            failures.append("EXTRACTION_RECEIPT_MISSING:" + identifier)
        elif extraction.get("source_hash") != source["source_hash"] or extraction.get("source_video") != source["source_video"] or extraction.get("frames") != len(samples):
            failures.append("EXTRACTION_RECEIPT_PROVENANCE_OR_COUNT_MISMATCH:" + identifier)
        if any(extraction.get(name) for name in ("decode_budget_reached", "frame_limit_reached", "sampling_budget_reached", "premature_decode_end")):
            failures.append("EXTRACTION_INCOMPLETE:" + identifier)
        extraction_totals["exact_duplicates_skipped"] += extraction.get("duplicate_frames_skipped", 0)
        extraction_totals["selected_retained"] += extraction.get("frames", 0)
        extraction_totals["sampled_candidates_before_exact_dedup"] += extraction.get("sampled_candidates", 0)
        if extraction.get("timing_fallback_frames"):
            warnings.append("CFR_FPS_TIMESTAMP_FALLBACK_REVIEW_FOR_VFR:" + identifier)
        per_session.append({"session_id": identifier, "original_filename": source.get("original_filename"),
                            "original_aliases": source.get("original_aliases", []),
                            "source_hash": source["source_hash"], "duration_seconds": media.get("duration_seconds"),
                            "media": media, "samples": len(samples),
                            "labels": dict(Counter(row["behavior_label"] or "UNANNOTATED" for row in samples)),
                            "split": sorted(memberships[identifier]), "experiment_metadata": source.get("session_metadata", {})})
    split_counts = {}
    for name in ("train", "validation", "test"):
        selected = [row for row in rows if row["session_id"] in set(splits.get(name, []))]
        available = Counter(task_label(row, "behavior_v2") for row in selected if row["usable"])
        if not splits.get(name):
            failures.append("EMPTY_SPLIT:" + name)
        for label in BEHAVIOR_V2:
            if not available[label]:
                failures.append("SPLIT_CLASS_COVERAGE:" + name + ":" + label)
        split_counts[name] = {"sessions": len(splits.get(name, [])), "samples": len(selected),
                              "usable_samples": sum(available[label] for label in BEHAVIOR_V2)}
    for label in BEHAVIOR_V2:
        if usable_labels[label] < min_class_samples:
            failures.append("INSUFFICIENT_LABEL_COVERAGE:" + label)
    if labels["UNANNOTATED"]:
        warnings.append("UNANNOTATED_SAMPLES_REMAIN_EXCLUDED_FROM_TRAINING")
    imbalance = bool(usable_labels and min(usable_labels.get(label, 0) for label in BEHAVIOR_V2) > 0 and
                     max(usable_labels.values())/min(usable_labels[label] for label in BEHAVIOR_V2) > 10)
    if imbalance:
        warnings.append("TRAINABLE_CLASS_IMBALANCE_GT_10_TO_1")
    hashes = Counter(row["hash"] for row in rows)
    if initial_snapshot != snapshot() or (root / ".dataset-write.lock").exists():
        failures.append("DATASET_CHANGED_OR_WRITER_ACTIVE_DURING_REPORT")
    return {"status": "NOT_READY" if failures else "READY_FOR_PILOT_TRAINING", "failures": sorted(set(failures)),
            "warnings": sorted(set(warnings)), "manifest_sha256": manifest_hash, "metadata_snapshot_sha256": initial_snapshot,
            "missing_metadata_warnings": sorted({item for item in warnings + failures if "METADATA" in item or "TIMESTAMP_MISSING" in item}),
            "source_videos": len(sources), "source_aliases_same_hash": sum(max(0, len(source.get("original_aliases", []))-1) for source in sources),
            "independent_source_groups": len(independent), "sessions": len(source_map),
            "total_known_source_duration_seconds": known_duration, "duration_basis": "reported average FPS/frame count, may be approximate",
            "samples_extracted_candidates": extraction_totals["sampled_candidates_before_exact_dedup"],
            "samples_extracted_retained": len(rows), "usable_trainable_samples": sum(usable_labels.values()),
            "extraction_totals": dict(extraction_totals), "exact_duplicates_retained": sum(count-1 for count in hashes.values()),
            "corrupt_samples": corrupt, "hash_mismatches": hash_mismatch, "blur_warnings": blur,
            "quality_unavailable": quality_unavailable, "near_duplicates": near, "near_review_accepted": reviewed,
            "leakage": {"failures": structural["failures"], "confirmed_leakage": bool(structural["failures"])},
            "per_label": {label: {"samples": labels[label], "usable_samples": usable_labels[label],
                                   "sample_coverage_seconds_estimate": round(coverage[label], 6)} for label in STATES},
            "label_duration_basis": "sum of retained sampling cells, NOT inferred full-video behavior duration or consumed time",
            "per_session": per_session, "split_counts": split_counts, "class_imbalance_warning": imbalance,
            "policy": {"min_class_samples": min_class_samples, "min_independent_source_groups": 3,
                       "blur_threshold": blur_threshold, "near_comparison_limit": near_comparison_limit,
                       "food_roi": "RED", "water_roi": "BLUE", "trainable_labels": list(BEHAVIOR_V2)},
            "training_performed": False, "actuation_enabled": False}


def markdown_report(result):
    lines = ["# Single-cat Behavior V2 readiness", "", "**" + result["status"] + "**", "",
             f"Source videos: {result['source_videos']}; independent groups: {result['independent_source_groups']}; retained samples: {result['samples_extracted_retained']}.",
             f"Known source duration: {result['total_known_source_duration_seconds']:.3f}s ({result['duration_basis']}).",
             f"Corrupt: {result['corrupt_samples']}; blur flags: {result['blur_warnings']}; near pairs: {result['near_duplicates']['pairs']}; near check complete: {result['near_duplicates']['complete']}.",
             "", "RED=FOOD; BLUE=WATER. Food variants across sessions are experiment metadata, not behavior classes.", "",
             "| Label | Samples | Usable | Sampling-cell coverage estimate (s) |", "|---|---:|---:|---:|"]
    for label, values in result["per_label"].items():
        lines.append(f"| {label} | {values['samples']} | {values['usable_samples']} | {values['sample_coverage_seconds_estimate']} |")
    lines += ["", result["label_duration_basis"], "", "## Splits", "", "| Split | Sessions | Samples | Usable |", "|---|---:|---:|---:|"]
    for name, values in result["split_counts"].items():
        lines.append(f"| {name} | {values['sessions']} | {values['samples']} | {values['usable_samples']} |")
    lines += ["", "## Sessions", "", "| Session | Original file | Duration s | Samples | Labels |", "|---|---|---:|---:|---|"]
    for item in result["per_session"]:
        filename = str(item["original_filename"]).replace("|", "/").replace("\n", " ")
        lines.append(f"| {item['session_id']} | {filename} | {item['duration_seconds']} | {item['samples']} | {item['labels']} |")
    lines += ["", "## Failed gates"] + ["- " + failure for failure in result["failures"]]
    lines += ["", "## Warnings"] + ["- " + warning for warning in result["warnings"]]
    lines += ["", "Near matches are review flags, not proven leakage. No samples were deleted, no labels invented, no model trained.",
              "Readiness is technical pilot eligibility, not accuracy/semantic certification or authorization to actuate.", ""]
    return "\n".join(lines)


def write_reports(result, output_dir):
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "readiness.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    with (folder / "readiness.md").open("x", encoding="utf-8") as stream:
        stream.write(markdown_report(result))
    return {"json": str(folder / "readiness.json"), "markdown": str(folder / "readiness.md")}


def new_report_dir(root):
    return Path(root) / "reports" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:8])
