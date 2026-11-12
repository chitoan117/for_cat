"""Bounded source-time extraction; CLI defaults to 2 FPS, never labels behavior."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

from ai.dataset import ROOT, ID_PATTERN, OPTIONAL, digest, load_manifest, validate_row
from ai.artifacts import parse_json, relative_file
from ai.label_schema import PREFERENCE_FIELDS
from ai.manifest_io import atomic_text, dataset_lock, rows_text
from ai.quality import image_quality
from ai.sampling import SamplingPolicy, fingerprint
from ai.scripts.import_video import VIDEO_BYTE_CAP, load_sources, session_metadata


def extract(name: str, session_id: str, root: Path = ROOT, *, every=30, max_frames=100,
            apply=False, metadata=None, interval_seconds=None, minimum_spacing=0,
            schema_version=1, resume=False, blur_threshold=50):
    root = Path(root)
    if type(schema_version) is not int or schema_version not in (1, 2):
        raise ValueError("schema version must be 1 or 2")
    if not ID_PATTERN.fullmatch(session_id) or Path(name).name != name:
        raise ValueError("invalid session or video name")
    allowed = OPTIONAL + (PREFERENCE_FIELDS if schema_version == 2 else ())
    if any(key not in allowed for key in (metadata or {})):
        raise ValueError("only optional context metadata may be supplied")
    metadata = session_metadata(metadata)
    if not 1 <= every <= 10000 or not 1 <= max_frames <= 10000:
        raise ValueError("invalid extraction bounds")
    if interval_seconds is not None and (not math.isfinite(interval_seconds) or interval_seconds <= 0):
        raise ValueError("invalid sampling interval")
    policy = SamplingPolicy(interval_seconds or 0.000001, minimum_spacing, max_samples=max_frames)
    source = relative_file(root / "raw", name)
    source_hash = digest(source, max_bytes=VIDEO_BYTE_CAP)
    settings = {"schema_version": schema_version, "every": every, "interval_seconds": interval_seconds,
                "minimum_spacing": minimum_spacing, "blur_threshold": blur_threshold}
    receipt_path = root / "extractions" / (session_id + ".json")
    with dataset_lock(root, apply):
        old, errors = load_manifest(root)
        if errors:
            raise ValueError("invalid existing manifest: " + "; ".join(errors[:3]))
        if resume and sum(row["session_id"] == session_id for row in old) > max_frames:
            raise ValueError("max_frames is below existing retained sample count; refusing receipt regression")
        if receipt_path.exists() and resume:
            previous = parse_json(receipt_path.read_text(encoding="utf-8"))
            if previous.get("settings") != settings or previous.get("source_hash") != source_hash:
                raise ValueError("extraction policy/source differs; use a new dataset version")
        catalog = load_sources(root)
        imported = next((item for item in catalog if item["source_hash"] == source_hash), None)
        if imported and imported["session_id"] != session_id:
            raise ValueError("source session mismatch; use the source receipt session ID")
        context = dict(metadata)
        if schema_version == 2 and imported:
            original_context = imported.get("session_metadata", {})
            if any(key in original_context and original_context[key] != value for key, value in context.items()):
                raise ValueError("source session metadata conflict")
            context = {**original_context, **context}
        by_id = {item["sample_id"]: item for item in old}
        by_time = {(item["source_hash"], item.get("source_offset_seconds")): item for item in old}
        hashes = {item["hash"] for item in old}
        additions, created = [], []
        committed = False
        count = found = duplicates = existing = selected = near = timing_fallbacks = 0
        sampling_budget = False
        try:
            import cv2
            from PIL import Image
        except ImportError as error:
            raise ValueError("OpenCV/Pillow required; no frames extracted") from error
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            cap.release()
            raise ValueError("video cannot be decoded")
        fps, reported_count = float(cap.get(cv2.CAP_PROP_FPS)), float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(reported_count) or reported_count <= 0:
            reported_count = float("nan")
        if not math.isfinite(fps) or fps <= 0:
            cap.release()
            raise ValueError("readable FPS required for source-time sampling")
        last_time = -1.0
        try:
            while found < max_frames and count < 100000:
                if len(policy.hashes) >= max_frames:
                    sampling_budget = True
                    break
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                frame_index = count
                count += 1
                seconds, clock = frame_index / fps, "frame_index_fps"
                if schema_version == 2:
                    pos = float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000
                    if math.isfinite(pos) and pos >= 0 and pos > last_time and (frame_index == 0 or pos > 0):
                        seconds, clock = pos, "decoder_pos_msec"
                    else:
                        timing_fallbacks += 1
                seconds = round(seconds, 9)
                if seconds < last_time:
                    raise ValueError("source timestamps moved backwards")
                last_time = seconds
                if (interval_seconds is None and frame_index % every != 0) or not policy.due(seconds):
                    continue
                selected += 1
                ok, encoded = cv2.imencode(".jpg", frame)
                if not ok:
                    raise ValueError("could not encode extracted frame")
                data = encoded.tobytes()
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                quality = image_quality(image, blur_threshold) if schema_version == 2 else None
                previous_near = policy.near_warnings
                sha = policy.select(seconds, data, int(quality["dhash"], 16) if quality else fingerprint(image))
                if sha is None:
                    duplicates += 1
                    continue
                sample_id = "s-" + (hashlib.sha256(f"{source_hash}:{frame_index}".encode()).hexdigest()[:48]
                                     if schema_version == 2 else sha[:24])
                current = by_id.get(sample_id)
                if resume and current is None:
                    current = by_time.get((source_hash, seconds))
                if current is not None:
                    if not resume:
                        raise ValueError("sample already exists; use --resume")
                    if current["hash"] != sha or current["source_hash"] != source_hash or current["session_id"] != session_id:
                        raise ValueError("existing sample differs; refusing overwrite")
                    if current.get("frame_index", frame_index) != frame_index:
                        raise ValueError("existing source frame index differs")
                    if digest(relative_file(root, current["path"])) != sha:
                        raise ValueError("existing extracted image corrupt/changed")
                    existing += 1; found += 1
                    continue
                if sha in hashes:
                    duplicates += 1
                    continue
                path = f"processed/{sample_id}.jpg"
                item = {"sample_id": sample_id, "session_id": session_id, "source_video": name,
                        "timestamp": None, "source_offset_seconds": seconds, "identity_label": None,
                        "behavior_label": None, "usable": True, "hash": sha, "source_hash": source_hash, "path": path}
                item.update(context)
                if schema_version == 2:
                    quality["near_duplicate_warning"] = policy.near_warnings > previous_near
                    near += int(quality["near_duplicate_warning"])
                    item.update(schema_version=2, subject_label=None, usable=False, frame_index=frame_index,
                                sample_sequence=selected-1, timestamp_source=clock, quality=quality)
                problems = validate_row(item)
                if problems:
                    raise ValueError("invalid extracted metadata: " + "; ".join(problems))
                if apply:
                    output = relative_file(root, path)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    if output.exists():
                        if not resume or digest(output) != sha:
                            raise ValueError("unmanifested image conflict; no overwrite")
                    else:
                        with output.open("xb") as stream:
                            created.append(output)
                            stream.write(data)
                            stream.flush(); os.fsync(stream.fileno())
                additions.append(item); hashes.add(sha); by_id[sample_id] = item
                found += 1
            ended_early = math.isfinite(reported_count) and reported_count > count + 2 and found < max_frames and count < 100000
            result = {"status": "EXTRACTED" if apply else "DRY_RUN", "frames": found, "new_frames": len(additions),
                      "sampled_candidates": selected,
                      "already_present": existing, "duplicate_frames_skipped": duplicates, "decoded": count,
                      "session_id": session_id, "source_hash": source_hash, "source_video": name,
                      "near_duplicate_warnings": policy.near_warnings, "new_near_flags": near,
                      "timing_fallback_frames": timing_fallbacks, "decode_budget_reached": count >= 100000,
                      "frame_limit_reached": found >= max_frames and (not math.isfinite(reported_count) or policy.next_at < reported_count/fps - 1/fps),
                      "sampling_budget_reached": sampling_budget,
                      "premature_decode_end": ended_early, "settings": settings}
            if apply:
                result["verified_at"] = datetime.now(timezone.utc).isoformat()
                if additions:
                    atomic_text(root / "manifest.jsonl", rows_text(old + additions))
                committed = True
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_text(receipt_path, json.dumps(result, indent=2, allow_nan=False) + "\n")
            return result
        finally:
            cap.release()
            if not committed:
                for output in created:
                    output.unlink(missing_ok=True) # only files exclusively created by this invocation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--every", type=int)
    parser.add_argument("--max-frames", type=int, default=10000)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--interval-seconds", type=float)
    parser.add_argument("--minimum-spacing", type=float, default=0)
    parser.add_argument("--schema-version", type=int, choices=(1, 2), default=1)
    parser.add_argument("--blur-threshold", type=float, default=50)
    for name in OPTIONAL:
        parser.add_argument("--" + name.replace("_", "-"))
    args = parser.parse_args()
    interval = args.interval_seconds if args.interval_seconds is not None else (None if args.every else 0.5)
    try:
        context = {name: getattr(args, name) for name in OPTIONAL if getattr(args, name) is not None}
        print(json.dumps(extract(args.source_video, args.session_id, args.dataset, every=args.every or 30,
                                 max_frames=args.max_frames, apply=args.apply, resume=args.resume, metadata=context,
                                 interval_seconds=interval, minimum_spacing=args.minimum_spacing,
                                 schema_version=args.schema_version, blur_threshold=args.blur_threshold), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"EXTRACTION_FAILED: {exc}\n")
