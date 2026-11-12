"""Human-reviewed, half-open time intervals; no AI prelabels or automatic truth."""
from bisect import bisect_right
import copy
import math
from pathlib import Path

from ai.artifacts import read_json
from ai.dataset import ID_PATTERN, load_manifest
from ai.label_schema import BEHAVIOR_V2
from ai.manifest_io import dataset_lock, replace_manifest
from ai.scripts.import_video import load_sources
from ai.scripts.label_dataset import set_label

LABELS = BEHAVIOR_V2 + ("NONE", "UNKNOWN", "UNSURE")


def seconds(value):
    if isinstance(value, str):
        parts = value.split(":")
        if not 1 <= len(parts) <= 3:
            raise ValueError("time must be seconds, MM:SS.s or HH:MM:SS.s")
        try:
            numbers = [float(part) for part in parts]
        except ValueError as error:
            raise ValueError("invalid interval time") from error
        if any(not math.isfinite(number) or number < 0 for number in numbers) or any(number >= 60 for number in numbers[1:]):
            raise ValueError("invalid interval time")
        result = sum(number * 60**index for index, number in enumerate(reversed(numbers)))
    elif type(value) in (int, float):
        result = value
    else:
        raise ValueError("invalid interval time type")
    if not math.isfinite(result) or not 0 <= result <= 1_000_000:
        raise ValueError("invalid interval time range")
    return result


def reviewed_intervals(document):
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int or document.get("schema_version") != 2 or document.get("annotation_source") != "HUMAN_REVIEWED":
        raise ValueError("interval document requires schema_version=2 and explicit annotation_source=HUMAN_REVIEWED")
    if set(document) - {"schema_version", "annotation_source", "session_id", "source_hash", "reviewer", "notes", "intervals"}:
        raise ValueError("unknown interval-document field; predictions cannot be silently accepted")
    if not isinstance(document.get("session_id"), str) or not ID_PATTERN.fullmatch(document["session_id"]):
        raise ValueError("invalid interval session")
    for name in ("reviewer", "notes"):
        if name in document and (not isinstance(document[name], str) or len(document[name]) > 256):
            raise ValueError("invalid annotation notes/reviewer")
    values = document.get("intervals")
    if not isinstance(values, list) or not 1 <= len(values) <= 10000:
        raise ValueError("provide 1..10000 human-reviewed intervals")
    ranges = []
    for item in values:
        if not isinstance(item, dict) or set(item) != {"start", "end", "label"} or item["label"] not in LABELS:
            raise ValueError("invalid interval label/fields")
        first, last = seconds(item["start"]), seconds(item["end"])
        if last <= first:
            raise ValueError("interval must have positive duration")
        ranges.append({"start": first, "end": last, "label": item["label"]})
    ranges.sort(key=lambda item: item["start"])
    if any(left["end"] > right["start"] for left, right in zip(ranges, ranges[1:])):
        raise ValueError("overlapping intervals rejected")
    return ranges


def annotate_intervals(root, document_path, *, session_id=None, apply=False, replace=False,
                       boundary_seconds=0.25, boundary_label="UNSURE"):
    root = Path(root)
    document = read_json(Path(document_path))
    ranges = reviewed_intervals(document)
    identifier = document["session_id"]
    if session_id is not None and session_id != identifier:
        raise ValueError("CLI/document session mismatch")
    if not math.isfinite(boundary_seconds) or not 0 <= boundary_seconds <= 5 or boundary_label not in ("UNKNOWN", "UNSURE"):
        raise ValueError("invalid transition boundary policy")
    with dataset_lock(root, apply):
        rows, errors = load_manifest(root)
        if errors:
            raise ValueError("invalid manifest: " + "; ".join(errors[:3]))
        targets = [row for row in rows if row["session_id"] == identifier]
        if not targets or any(row.get("schema_version") != 2 for row in targets):
            raise ValueError("interval annotation requires an extracted schema-v2 session")
        hashes = {row["source_hash"] for row in targets}
        if len(hashes) != 1 or document.get("source_hash") not in hashes:
            raise ValueError("source_hash required and must match the session video")
        source = next((item for item in load_sources(root) if item["session_id"] == identifier), {})
        media = source.get("media", {})
        duration, fps = media.get("duration_seconds"), media.get("fps")
        if duration is not None and ranges[-1]["end"] > duration + (1 / fps if fps else 0.001):
            raise ValueError("interval extends beyond reported source duration")
        starts = [item["start"] for item in ranges]
        boundaries = sorted({value for item in ranges for value in (item["start"], item["end"])
                             if value > 0 and (duration is None or value < duration - 1e-9)} -
                            {left["end"] for left, right in zip(ranges, ranges[1:])
                             if left["end"] == right["start"] and left["label"] == right["label"]})
        changed = matched = uncertainty = 0
        for item in targets:
            offset = item.get("source_offset_seconds")
            if offset is None:
                raise ValueError("session sample has no source timestamp")
            position = bisect_right(starts, offset) - 1
            chosen = ranges[position] if position >= 0 and offset < ranges[position]["end"] else None
            updated = copy.deepcopy(item)
            if chosen:
                matched += 1
                behavior = chosen["label"]
                edge_index = bisect_right(boundaries, offset)
                closest_edges = boundaries[max(0, edge_index-1):edge_index+1]
                if behavior not in ("UNKNOWN", "UNSURE") and boundary_seconds and any(abs(offset-edge) <= boundary_seconds for edge in closest_edges):
                    behavior = boundary_label
                    uncertainty += 1
                subject = "CAT" if behavior in BEHAVIOR_V2 else behavior
                set_label(updated, None, behavior, subject=subject, replace=True)
            elif replace:
                updated.update(subject_label=None, identity_label=None, behavior_label=None, usable=False)
            if updated != item:
                if not replace and item.get("behavior_label") is not None:
                    raise ValueError("existing annotation conflicts; review then use --replace for whole-session correction")
                item.update(updated)
                changed += 1
        revision = None
        if apply and changed:
            revision = replace_manifest(root, rows, action="HUMAN_SESSION_INTERVALS", details={
                "session_id": identifier, "document": document, "normalized_intervals": ranges,
                "boundary_seconds": boundary_seconds, "boundary_label": boundary_label,
                "replace_whole_session": replace, "changed_samples": changed})
        return {"status": "ANNOTATED" if apply and changed else "UNCHANGED" if apply else "DRY_RUN",
                "session_id": identifier, "matched_samples": matched, "changed_samples": changed,
                "boundary_review_samples": uncertainty, "revision": revision, "ground_truth_source": "HUMAN_REVIEWED"}
