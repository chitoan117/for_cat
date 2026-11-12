"""Copy an opt-in source video under an anonymized hash name; no frames yet."""

import argparse
import json
import shutil
from pathlib import Path

from ai.dataset import ROOT, ID_PATTERN, digest


def import_video(source: Path, session_id: str, root: Path = ROOT, *, apply: bool = False) -> dict:
    if not ID_PATTERN.fullmatch(session_id):
        raise ValueError("invalid anonymous session ID")
    if source.suffix.lower() not in (".mp4", ".avi", ".mov", ".mkv"):
        raise ValueError("supported video extension required")
    sha = digest(source)
    name = f"video-{sha[:24]}{source.suffix.lower()}"
    dest = root / "raw" / name
    if dest.exists():
        raise ValueError("source already imported; will not overwrite")
    receipt = {"session_id": session_id, "source_hash": sha, "source_video": name}
    if apply:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as inp, dest.open("xb") as out:
            shutil.copyfileobj(inp, out, 1024 * 1024)
        with (root / "sources.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(receipt, sort_keys=True) + "\n")
    return {"status": "IMPORTED" if apply else "DRY_RUN", **receipt}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(import_video(args.source, args.session_id, args.dataset, apply=args.apply)))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"IMPORT_FAILED: {exc}\n")
