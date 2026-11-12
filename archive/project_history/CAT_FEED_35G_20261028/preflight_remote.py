"""Read-only live Jetson inventory for the requested CAT-only35g demo (Python3.6+)."""
import glob
import hashlib
import json
import os
from pathlib import Path
import subprocess


def command(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
    return {"code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


root = Path("/home/toan/for_cat")
out = {"hostname": command(["hostname"]), "root_exists": root.is_dir(),
       "home_entries": sorted(os.listdir("/home/toan")), "serial_by_id": glob.glob("/dev/serial/by-id/*"),
       "video_devices": glob.glob("/dev/video*"), "changes_performed": False}
out["units"] = command(["systemctl", "show", "-p", "Id", "-p", "LoadState", "-p", "ActiveState", "-p", "ExecStart",
                         "for-cat-ai.service", "for-cat-api.service", "for-cat-esp32-bridge.service", "forr-cat.service"])
if root.is_dir():
    out["root_entries"] = sorted(os.listdir(str(root)))
    out["git"] = {"head": command(["git", "-C", str(root), "rev-parse", "HEAD"]),
                  "status": command(["git", "-C", str(root), "status", "--porcelain=v1"])}
    paths = ["jetson/ai/cat_dog_trt.cpp", "jetson/ai/cat_dog_trt", "jetson/device/ai_state_tap.cpp",
             "models/tensorrt/yolov8n_320_fp16.engine", ".native-build/esp32/ai_state_tap", "jetson/data/events.db",
             ".venv/jetson-integration/bin/python", "scripts/run_existing_ai.sh", ".git/index"]
    out["paths"] = {}
    for name in paths:
        path = root / name
        info = {"exists": path.exists()}
        if path.is_file():
            info["bytes"] = path.stat().st_size
            if name != "jetson/data/events.db":
                info["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        out["paths"][name] = info
    out["ai_directory"] = sorted(os.listdir(str(root / "jetson/ai"))) if (root / "jetson/ai").is_dir() else []
out["sudo_noninteractive"] = command(["sudo", "-n", "true"])
print(json.dumps(out, indent=2))
