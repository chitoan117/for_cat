"""Explicit source-video import and idempotent directory import; no labels inferred."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

from ai.artifacts import parse_json, relative_file
from ai.dataset import ROOT, ID_PATTERN, OPTIONAL, digest
from ai.label_schema import PREFERENCE_FIELDS, preference_error
from ai.manifest_io import atomic_text, dataset_lock, rows_text

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
VIDEO_BYTE_CAP = 20_000_000_000


def load_sources(root):
    path = Path(root) / "sources.jsonl"
    if not path.exists():
        return []
    if not path.is_file() or path.stat().st_size > 20_000_000:
        raise ValueError("invalid/oversized source catalog")
    rows = [parse_json(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    hashes, sessions = set(), set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("session_id"), str) or not ID_PATTERN.fullmatch(row["session_id"]):
            raise ValueError("invalid source session")
        sha = row.get("source_hash", "")
        if not isinstance(sha, str) or len(sha) != 64 or any(char not in "0123456789abcdef" for char in sha):
            raise ValueError("invalid source hash")
        if sha in hashes or row["session_id"] in sessions:
            raise ValueError("duplicate source hash/session in catalog")
        hashes.add(sha); sessions.add(row["session_id"])
        relative_file(Path(root) / "raw", row.get("source_video", ""))
        session_metadata(row.get("session_metadata"))
        media = row.get("media", {})
        if not isinstance(media, dict):
            raise ValueError("invalid source media metadata")
        if "readable" in media and type(media["readable"]) is not bool:
            raise ValueError("invalid media readability flag")
        for name in ("duration_seconds", "fps", "frame_count", "width", "height"):
            value = media.get(name)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
                raise ValueError("invalid source media measurement")
    return rows


def session_metadata(value):
    if value is not None and not isinstance(value, dict):
        raise ValueError("session metadata must be an object")
    value = dict(value or {})
    if any(name not in OPTIONAL + PREFERENCE_FIELDS for name in value):
        raise ValueError("unknown session metadata field")
    for name in OPTIONAL:
        if name in value and value[name] is not None and (not isinstance(value[name], str) or len(value[name]) > (256 if name == "notes" else 64)):
            raise ValueError("invalid session context")
    problem = preference_error(value)
    if problem:
        raise ValueError(problem)
    return value


def probe_video(path):
    result = {"readable": False, "duration_seconds": None, "fps": None, "frame_count": None,
              "width": None, "height": None, "duration_source": "opencv_frame_count_over_fps"}
    try:
        import cv2
    except ImportError:
        return {**result, "warning": "OPENCV_UNAVAILABLE"}
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return {**result, "warning": "VIDEO_UNREADABLE"}
        ok, frame = cap.read()
        if not ok or frame is None:
            return {**result, "warning": "FIRST_FRAME_UNREADABLE"}
        result.update(readable=True, width=int(frame.shape[1]), height=int(frame.shape[0]))
        fps, count = float(cap.get(cv2.CAP_PROP_FPS)), float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if math.isfinite(fps) and fps > 0:
            result["fps"] = fps
        if math.isfinite(count) and count > 0:
            result["frame_count"] = int(count)
        if result["fps"] and result["frame_count"]:
            result["duration_seconds"] = result["frame_count"] / result["fps"]
        return result
    finally:
        cap.release()


def import_video(source: Path, session_id: str | None, root: Path = ROOT, *, apply=False,
                 resume=False, metadata=None, original_relative_path=None):
    source, root = Path(source), Path(root)
    if session_id is not None and not ID_PATTERN.fullmatch(session_id):
        raise ValueError("invalid anonymous session ID")
    if source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("supported video extension required")
    metadata = session_metadata(metadata)
    sha = digest(source, max_bytes=VIDEO_BYTE_CAP)
    session_id = session_id or ("v-" + sha[:48])
    alias = original_relative_path or source.name
    with dataset_lock(root, apply):
        catalog = load_sources(root)
        existing = next((row for row in catalog if row["source_hash"] == sha), None)
        if existing:
            if not resume:
                raise ValueError("source already imported; will not overwrite")
            if any(existing.get("session_metadata", {}).get(key) != value for key, value in metadata.items()):
                raise ValueError("session metadata conflict; do not silently redefine an existing experiment")
            dest = relative_file(root / "raw", existing["source_video"])
            if digest(dest, max_bytes=VIDEO_BYTE_CAP) != sha:
                raise ValueError("imported source changed/corrupt")
            aliases = existing.setdefault("original_aliases", [existing.get("original_relative_path", existing.get("original_filename", source.name))])
            if alias not in aliases:
                aliases.append(alias)
                if apply:
                    atomic_text(root / "sources.jsonl", rows_text(catalog, limit=20_000_000))
            return {**existing, "status": "ALREADY_IMPORTED"}
        if any(row["session_id"] == session_id for row in catalog):
            raise ValueError("session ID collision with a different source video")
        name = f"video-{sha[:24]}{source.suffix.lower()}"
        dest = relative_file(root / "raw", name)
        if dest.exists() and digest(dest, max_bytes=VIDEO_BYTE_CAP) != sha:
            raise ValueError("source filename hash-prefix collision; no overwrite")
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                temporary = None
                try:
                    with source.open("rb") as inp:
                        with tempfile.NamedTemporaryFile(mode="wb", dir=dest.parent, prefix=".import-", suffix=".part", delete=False) as out:
                            temporary = Path(out.name)
                            shutil.copyfileobj(inp, out, 1024*1024)
                            out.flush(); os.fsync(out.fileno())
                    if digest(temporary, max_bytes=VIDEO_BYTE_CAP) != sha:
                        raise ValueError("source changed during import")
                    # Publish a COMPLETE copied inode, exclusive even against external writers.
                    # This is a link to our temporary COPY, never a link to the user's original.
                    try:
                        os.link(temporary, dest)
                    except FileExistsError:
                        if digest(dest, max_bytes=VIDEO_BYTE_CAP) != sha:
                            raise ValueError("source staging conflict; no overwrite")
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        receipt = {"schema_version": 2, "session_id": session_id, "source_hash": sha, "source_video": name,
                   "original_filename": source.name, "original_relative_path": alias, "original_aliases": [alias],
                   "import_timestamp": datetime.now(timezone.utc).isoformat() if apply else None,
                   "session_metadata": {"food_bowl_position": "RED_FOOD_ROI", **metadata},
                   "media": probe_video(dest if apply else source)}
        if apply:
            atomic_text(root / "sources.jsonl", rows_text(catalog + [receipt], limit=20_000_000))
        return {"status": "IMPORTED" if apply else "DRY_RUN", **receipt}


def import_directory(videos_dir, root=ROOT, *, apply=False, metadata_document=None):
    directory = Path(videos_dir)
    if not directory.is_dir():
        raise ValueError("videos directory missing")
    document = {} if metadata_document is None else metadata_document
    if not isinstance(document, dict) or set(document) - {"defaults", "videos"}:
        raise ValueError("metadata document must contain defaults/videos only")
    defaults = session_metadata(document.get("defaults"))
    by_video = document.get("videos", {})
    if not isinstance(by_video, dict):
        raise ValueError("videos metadata must be a relative-path mapping")
    paths = sorted(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)
    results, planned = [], {}
    for path in paths:
        relative = path.relative_to(directory).as_posix()
        metadata = session_metadata({**defaults, **session_metadata(by_video.get(relative))})
        result = import_video(path, None, root, apply=apply, resume=True,
                              metadata=metadata, original_relative_path=relative)
        sha = result["source_hash"]
        if not apply and sha in planned:
            if any(planned[sha]["session_metadata"].get(key) != value for key, value in metadata.items()):
                raise ValueError("duplicate input has conflicting experiment metadata")
            result = {**planned[sha], "status": "DUPLICATE_INPUT", "duplicate_filename": relative}
        results.append(result); planned[sha] = result
    return {"status": "IMPORTED_DIRECTORY" if apply else "DRY_RUN", "input_files": len(paths),
            "independent_sources": len({row["source_hash"] for row in results}), "sources": results,
            "unused_metadata_keys": sorted(set(by_video) - {path.relative_to(directory).as_posix() for path in paths})}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--session-id")
    parser.add_argument("--videos-dir", type=Path)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        document = parse_json(args.metadata.read_text(encoding="utf-8-sig")) if args.metadata else None
        if args.videos_dir:
            if args.source or args.session_id:
                raise ValueError("choose directory import or source/session import")
            result = import_directory(args.videos_dir, args.dataset, apply=args.apply, metadata_document=document)
        elif args.source and args.session_id:
            result = import_video(args.source, args.session_id, args.dataset, apply=args.apply, resume=args.resume, metadata=document)
        else:
            raise ValueError("supply --videos-dir or source + --session-id")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"IMPORT_FAILED: {exc}\n")
