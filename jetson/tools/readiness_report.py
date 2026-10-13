"""Passive local preparation report: no camera/serial/GPU open, no DB creation."""

import argparse
import importlib.util
import json
import platform
import shutil
import sqlite3
import sys
from pathlib import Path

from app.config import HardwareConfig


def is_jetson() -> bool:
    return platform.system() == "Linux" and Path("/etc/nv_tegra_release").is_file()


def report(settings: HardwareConfig | None = None) -> dict:
    settings = settings or HardwareConfig.from_env()
    packages = {name: importlib.util.find_spec(name) is not None for name in ("fastapi", "uvicorn", "serial", "cv2")}
    sections = {
        "JETSON_RUNTIME": {"state": "PARTIAL" if all(packages[x] for x in ("fastapi", "uvicorn", "serial")) else "NOT_AVAILABLE",
                           "python": platform.python_version(), "minimum_python": "3.10", "os": platform.system(),
                           "architecture": platform.machine(), "jetson_detected": is_jetson(), "validated": False},
        "CAMERA": {"state": "UNVERIFIED" if settings.camera_provider != "MOCK" else "NOT_CONFIGURED",
                   "provider": settings.camera_provider, "device": settings.camera_device,
                   "backend": settings.capture.backend, "opened": False},
        "SERIAL": {"state": "UNVERIFIED" if settings.esp32_serial_device else "NOT_CONFIGURED",
                   "device": settings.esp32_serial_device, "baud": settings.serial_baud, "opened": False},
        "DATABASE": {"state": "PARTIAL", "path": settings.db_path, "sqlite_version": sqlite3.sqlite_version,
                     "exists": Path(settings.db_path).is_file(), "probed_or_created": False},
        "AI_RUNTIME": {"state": "NOT_CONFIGURED" if settings.ai_runtime != "MOCK" else "UNVERIFIED",
                       "runtime": settings.ai_runtime, "shadow_mode": settings.ai_shadow_mode,
                       "model_loaded": False, "cuda_tool_present": bool(shutil.which("nvcc")),
                       "tensorrt_module_present": importlib.util.find_spec("tensorrt") is not None},
        "API": {"state": "PARTIAL" if packages["fastapi"] and packages["uvicorn"] else "NOT_AVAILABLE",
                "host": settings.api_host, "port": settings.api_port, "server_probed": False},
    }
    opencv = {"available": packages["cv2"], "gstreamer": "UNVERIFIED", "cuda": "UNVERIFIED"}
    if packages["cv2"]:
        try:
            import cv2
            opencv["version"] = cv2.__version__
            opencv["build_summary"] = [line.strip() for line in cv2.getBuildInformation().splitlines()
                                        if any(key in line for key in ("GStreamer", "NVIDIA CUDA", "v4l/v4l2", "Video I/O:"))]
            for line in opencv["build_summary"]:
                if "GStreamer:" in line:
                    opencv["gstreamer"] = line.split(":", 1)[1].strip()
                if "NVIDIA CUDA:" in line:
                    opencv["cuda"] = line.split(":", 1)[1].strip()
        except Exception:
            opencv["available"] = False
    return {"label": "NOT JETSON VERIFIED", "sections": sections, "dependencies": packages,
            "opencv": opencv, "python_supported": sys.version_info >= (3, 10)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = report()
    except ValueError as exc:
        parser.exit(2, f"NOT_CONFIGURED: {exc}\n")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["label"])
        for component, state in result["sections"].items():
            print(f"{component}: {state['state']} — {json.dumps(state)}")
        print("OpenCV:", json.dumps(result["opencv"]))
