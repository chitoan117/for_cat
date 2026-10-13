"""Manual bounded camera benchmark. Child process enforces total wall timeout; no image saved."""

import argparse
import json
import subprocess
import sys
import time
from statistics import mean

from app.camera.settings import CaptureSettings
from app.camera.usb_webcam import UsbWebcamCameraProvider
from tools.readiness_report import is_jetson


def benchmark(camera, settings: CaptureSettings, seconds=5, clock=time.monotonic):
    attempted = received = failures = 0
    intervals = []
    actual = None
    previous = None
    started = clock()
    try:
        if not camera.open():
            return {"status": "NOT_AVAILABLE", "frames_received": 0}
        while clock() - started < seconds and attempted < 10000:
            attempted += 1
            frame = camera.read()
            now = clock()
            if frame is None:
                failures += 1
                if failures >= settings.failure_threshold:
                    break
                continue
            received += 1
            actual = [frame.width, frame.height]
            if previous is not None:
                intervals.append(now - previous)
            previous = now
    finally:
        camera.close()
    elapsed = max(clock() - started, 1e-9)
    process = {"cpu_seconds": None, "max_rss_kib": None}
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        process = {"cpu_seconds": usage.ru_utime + usage.ru_stime,
                   "max_rss_kib": usage.ru_maxrss if sys.platform.startswith("linux") else None}
    except ImportError:
        pass
    return {"status": "MEASURED" if received else "NOT_AVAILABLE",
            "label": "JETSON BENCHMARK" if is_jetson() else "HOST BENCHMARK ONLY",
            "requested_resolution": [settings.width, settings.height], "actual_resolution": actual,
            "requested_fps": settings.fps, "measured_fps": received / elapsed,
            "frames_attempted": attempted, "frames_received": received, "failures": failures,
            "mean_frame_interval_seconds": mean(intervals) if intervals else None,
            "max_frame_interval_seconds": max(intervals) if intervals else None,
            "runtime_seconds": elapsed, "backend": settings.backend,
            "actual_backend": getattr(camera, "actual", {}).get("backend", "UNVERIFIED"),
            "process_usage_approximate": process,
            "read_timeout_supported": getattr(camera, "timeout_supported", False), "image_saved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, help="explicit detected node or Windows numeric index")
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--backend", choices=("AUTO", "V4L2", "GSTREAMER"), default="AUTO")
    parser.add_argument("--gstreamer-pipeline")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error("seconds must be >0 and <=30")
    if not args.worker:
        try:
            result = subprocess.run([sys.executable, "-m", "tools.benchmark_camera", *sys.argv[1:], "--worker"],
                                    capture_output=True, text=True, timeout=args.seconds + 5)
            print(result.stdout or json.dumps({"status": "NOT_AVAILABLE", "error": result.stderr[-512:]}))
            sys.exit(result.returncode)
        except subprocess.TimeoutExpired:
            print(json.dumps({"status": "NOT_AVAILABLE", "reason": "camera driver timed out; child terminated"}))
            sys.exit(2)
    settings = CaptureSettings(args.width, args.height, args.fps, args.backend, args.gstreamer_pipeline)
    device = int(args.device) if args.device.isdecimal() else args.device
    result = benchmark(UsbWebcamCameraProvider(device, settings=settings), settings, args.seconds)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "MEASURED" else 2)
