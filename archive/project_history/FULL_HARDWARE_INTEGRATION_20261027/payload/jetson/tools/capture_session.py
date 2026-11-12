"""Run explicitly: no physical webcam opens without --apply and camera:DEVICE."""
import argparse
import json
import sys
from pathlib import Path

# Permit the documented invocation from jetson/ without installing research packages.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ai.capture import capture, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="camera:0, camera:ACTUAL_NODE, or supplied video path")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--behavior", required=True)
    parser.add_argument("--output", type=Path, default=Path("../ai/datasets/capture"))
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--minimum-spacing", type=float, default=0.5)
    parser.add_argument("--max-frames", type=int, default=100)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    for name in ("food_type", "lighting", "distance", "view_angle", "occlusion", "environment", "notes"):
        parser.add_argument("--"+name.replace("_", "-"))
    args = parser.parse_args()
    try:
        metadata = plan(args.source, args.session_id, args.identity, args.behavior,
            duration=args.duration, interval=args.interval, minimum_spacing=args.minimum_spacing,
            max_frames=args.max_frames, **{key: getattr(args, key) for key in
            ("food_type", "lighting", "distance", "view_angle", "occlusion", "environment", "notes")})
        print(json.dumps(capture(metadata, args.output, apply=args.apply), indent=2))
    except (ValueError, OSError, EOFError) as exc:
        parser.exit(2, f"CAPTURE_FAILED: {exc}\n")


if __name__ == "__main__":
    main()
