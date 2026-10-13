"""Bounded one-frame manual-inspection test. No dataset or inference."""

import argparse
import sys
import tempfile
import time
from pathlib import Path

from app.camera.usb_webcam import UsbWebcamCameraProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Test one explicitly selected Linux device or Windows camera index")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--device", help="detected /dev/video* device (Linux)")
    source.add_argument("--camera-index", type=int, help="OpenCV camera index 0..16 (Windows PC)")
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error("--seconds must be > 0 and <= 30")
    if args.camera_index is not None and not 0 <= args.camera_index <= 16:
        parser.error("--camera-index must be 0..16")
    if args.device is not None and not Path(args.device).exists():
        print(f"Camera device not found: {args.device}")
        return 2
    selected = args.device if args.device is not None else args.camera_index
    camera = UsbWebcamCameraProvider(selected)
    successes = failures = 0
    resolution = None
    frame_file = None
    try:
        if not camera.open():
            print("Camera could not be opened (check device permissions and OpenCV)")
            return 2
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            frame = camera.read()
            if frame is None:
                failures += 1
                time.sleep(0.05)
                continue
            successes += 1
            resolution = (frame.width, frame.height)
            if frame_file is None:
                import cv2
                import numpy as np

                output = Path(tempfile.mkdtemp(prefix="forr-cat-hardware-test-"))
                channels = 3 if frame.pixel_format == "BGR" else 1
                shape = (frame.height, frame.width, channels) if channels == 3 else (frame.height, frame.width)
                image = np.frombuffer(frame.pixels, dtype=np.uint8).reshape(shape)
                candidate = output / "single-test-frame.jpg"
                if cv2.imwrite(str(candidate), image):
                    frame_file = candidate
                else:
                    print("Could not save manual-inspection frame")
                    frame_file = "save failed"
        elapsed = time.monotonic() - start
        print(f"{'camera_index' if args.camera_index is not None else 'device'}={selected} "
              f"resolution={resolution} frames={successes} "
              f"failures={failures} approximate_fps={successes / elapsed:.2f} "
              f"elapsed_seconds={elapsed:.2f} test_frame={frame_file}")
        return 0 if successes else 1
    finally:
        camera.close()


if __name__ == "__main__":
    sys.exit(main())
