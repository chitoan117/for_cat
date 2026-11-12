"""Import one manually selected frame with anonymous, session-scoped metadata."""

import argparse
import json
import shutil
from pathlib import Path

from ai.dataset import ROOT, OPTIONAL, append_row, digest, image_integrity, ID_PATTERN


def import_capture(source: Path, session_id: str, root: Path = ROOT, *, apply: bool = False,
                   metadata: dict | None = None) -> dict:
    if not ID_PATTERN.fullmatch(session_id):
        raise ValueError("session ID must be anonymous [a-z0-9_-], <=64 chars")
    if source.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise ValueError("JPEG/PNG capture required")
    integrity = image_integrity(source)
    if integrity != "OK":
        raise ValueError(f"image not verified: {integrity}")
    sha = digest(source)
    sample_id = f"s-{sha[:24]}"
    relative = f"processed/{sample_id}{source.suffix.lower()}"
    row = {"sample_id": sample_id, "session_id": session_id, "source_video": "",
           "timestamp": None, "identity_label": None, "behavior_label": None,
           "usable": True, "hash": sha, "source_hash": sha, "path": relative}
    if any(key not in OPTIONAL for key in (metadata or {})):
        raise ValueError("only optional context metadata may be supplied")
    row.update(metadata or {})  # append_row validates lengths
    if apply:
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as inp, dest.open("xb") as out:
            shutil.copyfileobj(inp, out, 1024 * 1024)
        try:
            return append_row(root, row, apply=True)
        except Exception:
            dest.unlink()  # only the new exclusive-create file
            raise
    return append_row(root, row, apply=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true", help="default is dry-run")
    for name in ("food_type", "lighting", "distance", "view_angle", "occlusion", "camera_device", "notes"):
        parser.add_argument("--" + name.replace("_", "-"))
    args = parser.parse_args()
    try:
        metadata = {name: getattr(args, name) for name in ("food_type", "lighting", "distance",
                    "view_angle", "occlusion", "camera_device", "notes") if getattr(args, name) is not None}
        print(json.dumps(import_capture(args.source, args.session_id, args.dataset,
                                        apply=args.apply, metadata=metadata)))
    except ValueError as exc:
        parser.exit(2, f"IMPORT_FAILED: {exc}\n")
