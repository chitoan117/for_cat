"""Linux video-node discovery without capture. Probing is explicit and process-bounded."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def list_devices(device_root=Path("/dev"), sys_root=Path("/sys/class/video4linux")) -> list[dict]:
    result = []
    for path in sorted(device_root.glob("video*"))[:32]:
        name_file = sys_root / path.name / "name"
        try:
            name = name_file.read_text(encoding="utf-8").strip()[:128] if name_file.is_file() else None
        except OSError:
            name = None
        result.append({"device": str(path), "name": name, "opened": False, "hardware_validated": False})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", help="explicit single device to probe; default opens none")
    args = parser.parse_args()
    print(json.dumps({"devices": list_devices()}, indent=2))
    if args.probe:
        try:
            probe = subprocess.run([sys.executable, "-m", "tools.benchmark_camera", "--device", args.probe,
                                    "--seconds", "1", "--worker"], capture_output=True, text=True, timeout=5)
            print(probe.stdout or json.dumps({"status": "NOT_AVAILABLE"}))
        except subprocess.TimeoutExpired:
            print(json.dumps({"status": "NOT_AVAILABLE", "reason": "probe timeout; child terminated"}))
