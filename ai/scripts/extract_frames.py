"""Stride-based, bounded, deterministic OpenCV extraction from an imported video."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, ID_PATTERN, OPTIONAL, append_row, digest
from ai.artifacts import relative_file
from ai.sampling import SamplingPolicy, fingerprint
import math


def extract(name: str, session_id: str, root: Path = ROOT, *, every: int = 30,
            max_frames: int = 100, apply: bool = False, metadata: dict | None = None,
            interval_seconds: float | None = None, minimum_spacing: float = 0) -> dict:
    if not ID_PATTERN.fullmatch(session_id) or Path(name).name != name:
        raise ValueError("invalid session or video name")
    if any(key not in OPTIONAL for key in (metadata or {})):
        raise ValueError("only optional context metadata may be supplied")
    if not 1 <= every <= 10000 or not 1 <= max_frames <= 1000:
        raise ValueError("invalid extraction bounds")
    policy = SamplingPolicy(interval_seconds or 0.000001,minimum_spacing)
    if interval_seconds is not None and (not math.isfinite(interval_seconds) or interval_seconds<=0):
        raise ValueError("invalid sampling interval")
    source = relative_file(root / "raw", name)
    source_hash = digest(source)
    try:
        import cv2
    except ImportError as exc:
        raise ValueError("OpenCV unavailable; no frames extracted") from exc
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        cap.release()
        raise ValueError("video cannot be decoded")
    count = found = duplicates = 0
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if (interval_seconds is not None or minimum_spacing>0) and (not math.isfinite(fps) or fps<=0):
        cap.release(); raise ValueError("FPS required for deterministic temporal sampling")
    try:
        while found < max_frames and count < 100000:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
            seconds = (count-1)/fps if math.isfinite(fps) and fps>0 else count-1
            if interval_seconds is None and (count - 1) % every != 0 or not policy.due(seconds):
                continue
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                raise ValueError(f"could not encode frame {count}")
            data = encoded.tobytes()
            from PIL import Image
            sha = policy.select(seconds,data,fingerprint(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))))
            if sha is None:
                duplicates += 1
                continue
            sample_id = f"s-{sha[:24]}"
            path = f"processed/{sample_id}.jpg"
            row = {"sample_id": sample_id, "session_id": session_id,
                   "source_video": name,
                   "timestamp": None, "source_offset_seconds": seconds,
                   "identity_label": None, "behavior_label": None, "usable": True,
                   "hash": sha, "source_hash": source_hash, "path": path}
            row.update(metadata or {})
            if apply:
                output = root / path
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("xb") as stream:
                    stream.write(data)
                try:
                    append_row(root, row, apply=True)
                except Exception:
                    output.unlink()
                    raise
            else:
                append_row(root, row, apply=False)
            found += 1
    finally:
        cap.release()
    return {"status": "EXTRACTED" if apply else "DRY_RUN", "frames": found,
            "duplicate_frames_skipped": duplicates,
            "decoded": count, "session_id": session_id,"near_duplicate_warnings":policy.near_warnings,
            "decode_budget_reached":count>=100000}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_video", help="anonymized video name in raw/")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--every", type=int, default=30)
    parser.add_argument("--max-frames", type=int, default=100)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--interval-seconds",type=float)
    parser.add_argument("--minimum-spacing",type=float,default=0)
    for name in ("food_type", "lighting", "distance", "view_angle", "occlusion", "camera_device", "notes"):
        parser.add_argument("--" + name.replace("_", "-"))
    args = parser.parse_args()
    try:
        metadata = {name: getattr(args, name) for name in ("food_type", "lighting", "distance",
                    "view_angle", "occlusion", "camera_device", "notes") if getattr(args, name) is not None}
        print(json.dumps(extract(args.source_video, args.session_id, args.dataset,
                                 every=args.every, max_frames=args.max_frames,
                                 apply=args.apply, metadata=metadata,interval_seconds=args.interval_seconds,
                                 minimum_spacing=args.minimum_spacing)))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"EXTRACTION_FAILED: {exc}\n")
