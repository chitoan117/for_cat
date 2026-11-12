"""Bounded raw RGB/BGR frame operations; no optional GPU/image packages required."""

from dataclasses import replace

from app.camera.base import CameraFrame
from app.vision.geometry import NormalizedBox


def channels(frame: CameraFrame) -> int:
    count = 1 if frame.pixel_format == "GRAY" else 3 if frame.pixel_format in ("RGB", "BGR") else 0
    if not count or frame.width <= 0 or frame.height <= 0 or len(frame.pixels) != frame.width * frame.height * count:
        raise ValueError("invalid raw frame layout")
    return count


def crop_frame(frame: CameraFrame, box: NormalizedBox) -> CameraFrame:
    count = channels(frame)
    x1, y1 = int(box.x1 * frame.width), int(box.y1 * frame.height)
    x2, y2 = min(frame.width, int(box.x2 * frame.width)), min(frame.height, int(box.y2 * frame.height))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("crop has no pixels")
    pixels = b"".join(frame.pixels[(y * frame.width + x1) * count:(y * frame.width + x2) * count]
                      for y in range(y1, y2))
    return replace(frame, pixels=pixels, width=x2-x1, height=y2-y1)


def limit_frame(frame: CameraFrame, max_width: int, max_height: int) -> CameraFrame:
    count = channels(frame)
    scale = min(1.0, max_width / frame.width, max_height / frame.height)
    if scale == 1.0:
        return frame
    width, height = max(1, int(frame.width * scale)), max(1, int(frame.height * scale))
    # Optional OpenCV fast path; CPU-only core fallback is deterministic nearest-neighbor.
    try:
        import cv2
        import numpy as np
        image = np.frombuffer(frame.pixels, np.uint8).reshape(frame.height, frame.width, count)
        pixels = cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST).tobytes()
    except ImportError:
        pixels = b"".join(frame.pixels[(int(y / scale) * frame.width + int(x / scale)) * count:
                                      (int(y / scale) * frame.width + int(x / scale)) * count + count]
                           for y in range(height) for x in range(width))
    return replace(frame, pixels=pixels, width=width, height=height)
