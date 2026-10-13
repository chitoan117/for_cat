"""Explicit opt-in bounded sampled-image capture. Nothing opens on import/dry-run."""
import hashlib
import json
import math
import multiprocessing as mp
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from ai.dataset import digest
from ai.sampling import SamplingPolicy, fingerprint
from ai.session import SessionManifest


def plan(source, session_id, identity, behavior, *, duration=60, interval=1,
         minimum_spacing=0.5, max_frames=100, recorded_at=None, **context):
    if source.startswith("camera:"):
        device = source[7:]
        if not device or (device.isdigit() and not 0 <= int(device) <= 16):
            raise ValueError("explicit camera device/index required")
        kind, source_hash, hash_kind = "CAMERA", None, "SAMPLED_FRAME_STREAM_SHA256"
    else:
        path = Path(source).resolve()
        if not path.is_file():
            raise ValueError("source video missing")
        device, kind, source_hash, hash_kind = str(path), "VIDEO", digest(path), "VIDEO_FILE_SHA256"
    return SessionManifest(session_id=session_id, recorded_at=recorded_at or datetime.now(timezone.utc),
        camera_source=kind, camera_device=device, identity_target=identity, behavior_target=behavior,
        duration_seconds=duration, sampling_interval_seconds=interval, minimum_spacing_seconds=minimum_spacing,
        max_frames=max_frames, source_hash=source_hash, source_hash_kind=hash_kind, **context)


def _record(manifest, folder, stop, capture_factory=None):
    import cv2  # only inside explicit recording, optional dependency
    from PIL import Image
    target = manifest.camera_device
    if manifest.camera_source == "CAMERA" and target.isdigit():
        target = int(target)
    cap = (capture_factory or cv2.VideoCapture)(target)
    policy = SamplingPolicy(manifest.sampling_interval_seconds, manifest.minimum_spacing_seconds)
    rows, total_bytes, stream_hash = [], 0, hashlib.sha256()
    start = time.monotonic()
    folder = Path(folder)
    reason = "DECODE_BUDGET"
    try:
        if not cap.isOpened():
            raise ValueError("capture cannot open explicit source")
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        fps = fps if math.isfinite(fps) and 0 < fps <= 1000 else None
        if manifest.camera_source == "VIDEO" and fps is None:
            raise ValueError("video FPS unavailable; cannot safely assign media offsets")
        manifest.fps = fps
        (folder / "processed").mkdir()
        for index in range(100_000):
            if stop.is_set():
                reason = "USER_STOP"; break
            if time.monotonic() - start >= manifest.duration_seconds:
                reason = "WALL_DURATION_LIMIT"; break
            ok, frame = cap.read()
            if not ok or frame is None:
                reason = "EOF" if manifest.camera_source == "VIDEO" else "CAMERA_READ_FAILURE"; break
            height, width = frame.shape[:2]
            SessionManifest.dimensions((width, height))
            manifest.resolution = (width, height)
            seconds = index / fps if manifest.camera_source == "VIDEO" else time.monotonic()-start
            if seconds >= manifest.duration_seconds:
                reason = "MEDIA_DURATION_LIMIT"; break
            if not policy.due(seconds):
                continue
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                raise ValueError("frame encoding failed")
            data = encoded.tobytes()
            if len(data) > 8_000_000 or total_bytes + len(data) > 100_000_000:
                reason = "STORAGE_BUDGET"; break
            perceptual = fingerprint(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            sha = policy.select(seconds, data, perceptual)
            if sha is None:
                continue
            sample_id = f"s-{sha[:24]}"
            relative = f"processed/{sample_id}.jpg"
            with (folder / relative).open("xb") as stream:
                stream.write(data)
            stream_hash.update(data)
            total_bytes += len(data)
            rows.append(dict(sample_id=sample_id, session_id=manifest.session_id, source_video="",
                timestamp=None, source_offset_seconds=seconds, identity_label=None, behavior_label=None,
                usable=False, hash=sha, source_hash=manifest.source_hash, path=relative,
                **{key: getattr(manifest, key) for key in ("food_type", "lighting", "distance", "view_angle", "occlusion")}))
            if len(rows) >= manifest.max_frames:
                reason = "FRAME_LIMIT"; break
    finally:
        cap.release()
    if manifest.camera_source == "CAMERA":
        manifest.source_hash = stream_hash.hexdigest() if rows else None
    for row in rows:
        row["source_hash"] = manifest.source_hash
    manifest.sample_count, manifest.stop_reason = len(rows), reason
    validated = SessionManifest.model_validate(manifest.model_dump())
    (folder / "session.json").write_text(validated.model_dump_json(indent=2), encoding="utf-8")
    (folder / "manifest.jsonl").write_text("".join(json.dumps(row, sort_keys=True)+"\n" for row in rows), encoding="utf-8")
    return {"status": "CAPTURED_UNANNOTATED", "samples": len(rows), "stop_reason": reason,
            "exact_duplicates_skipped": policy.duplicates, "near_duplicate_warnings": policy.near_warnings}


def _worker(payload, folder, stop, connection):
    try:
        connection.send(_record(SessionManifest.model_validate(payload), folder, stop))
    except Exception as exc:
        connection.send({"status": "CAPTURE_FAILED", "error": str(exc)[:256]})
    finally:
        connection.close()


def capture(manifest: SessionManifest, output: Path, *, apply=False):
    manifest = SessionManifest.model_validate(manifest.model_dump())
    output = Path(output)
    destination = output / manifest.session_id
    if destination.exists():
        raise FileExistsError("session already exists; no overwrite")
    if not apply:
        return {"status": "DRY_RUN", "manifest": manifest.model_dump(mode="json"), "camera_opened": False}
    output.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".capture-", dir=output))
    context = mp.get_context("spawn")
    stop = context.Event()
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(manifest.model_dump(mode="json"), str(stage), stop, sender))
    result = None
    try:
        process.start(); sender.close()
        deadline = time.monotonic() + manifest.duration_seconds + 10
        try:
            while time.monotonic() < deadline:
                if receiver.poll(0.1):
                    result = receiver.recv(); break
                if not process.is_alive():
                    break
        except KeyboardInterrupt:
            stop.set()
            if receiver.poll(3):
                result = receiver.recv()
        if result is None:
            raise TimeoutError("capture stopped: bounded worker deadline/read budget exceeded")
        process.join(3)
        if process.is_alive() or result["status"] == "CAPTURE_FAILED":
            raise ValueError(result.get("error", "worker did not terminate"))
        if destination.exists():
            raise FileExistsError("session already exists")
        stage.rename(destination)
        return {**result, "session_path": str(destination), "hardware_verified": False}
    finally:
        if process.pid is not None and process.is_alive():
            process.terminate(); process.join(3)
            if process.is_alive():
                process.kill(); process.join(3)
        receiver.close(); sender.close()
        if stage.exists():
            shutil.rmtree(stage)
