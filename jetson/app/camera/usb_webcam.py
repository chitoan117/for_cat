"""OpenCV camera provider; no image is persisted by the service."""

from datetime import datetime, timezone
from threading import RLock
from typing import Callable
import time

from app.camera.base import CameraFrame, CameraProvider
from app.camera.settings import CaptureSettings


class UsbWebcamCameraProvider(CameraProvider):
    def __init__(self, device: str | int | None, capture_factory: Callable | None = None,
                 settings: CaptureSettings | None = None):
        self.settings = settings or CaptureSettings()
        if (isinstance(device, int) and not 0 <= device <= 16) or \
                (not isinstance(device, int) and not device and self.settings.backend != "GSTREAMER"):
            raise ValueError("camera device path or index 0..16 is required")
        self.device = device
        self._capture_factory = capture_factory
        self._capture = None
        self._lock = RLock()
        self._state = "NOT_CONNECTED"
        self.failures = 0
        self.timeout_supported = False
        self.actual: dict = {}

    def open(self) -> bool:
        with self._lock:
            if self._capture is not None:
                try:
                    if self._capture.isOpened():
                        return True
                except Exception:
                    pass  # USB device can disappear between calls
            self.close()
            if self._capture_factory is None:
                try:
                    import cv2  # optional on mock-only installations
                except ImportError:
                    self._state = "NOT_AVAILABLE"
                    return False
                self._capture_factory = cv2.VideoCapture
            try:
                target = self.settings.pipeline if self.settings.backend == "GSTREAMER" else self.device
                backend = {"V4L2": 200, "GSTREAMER": 1800}.get(self.settings.backend)
                capture = self._capture_factory(target) if backend is None else self._capture_factory(target, backend)
                if not capture.isOpened():
                    capture.release()
                    self._state = "OFFLINE"
                    return False
                self._capture = capture
                if hasattr(capture, "set"):
                    capture.set(3, self.settings.width)
                    capture.set(4, self.settings.height)
                    capture.set(5, self.settings.fps)
                    capture.set(38, 1)  # buffer size: best effort
                    self.timeout_supported = bool(capture.set(54, self.settings.read_timeout_ms))
                if hasattr(capture, "get"):
                    self.actual = {"width": capture.get(3), "height": capture.get(4), "fps": capture.get(5)}
                if hasattr(capture, "getBackendName"):
                    self.actual["backend"] = capture.getBackendName()
                self._state = "NOT_VALIDATED"
                return True
            except Exception:  # third-party camera backends have varying exception types
                self._state = "OFFLINE"
                self.close()
                return False

    def read(self) -> CameraFrame | None:
        with self._lock:
            if not self.open():
                return None
            try:
                began = time.monotonic()
                ok, image = self._capture.read()
                now = time.monotonic()
                if not ok or image is None or now - began > self.settings.read_timeout_ms / 1000:
                    self.failures += 1
                    self._state = "OFFLINE"
                    self.close()
                    return None
                height, width = image.shape[:2]
                self.failures = 0
                self._state = "ONLINE"
                return CameraFrame(
                    captured_at=datetime.now(timezone.utc), pixels=image.tobytes(),
                    width=width, height=height, synthetic=False,
                    pixel_format="BGR" if len(image.shape) == 3 else "GRAY",
                    monotonic_seconds=now,
                )
            except Exception:  # a removed USB device may raise cv2.error
                self._state = "OFFLINE"
                self.failures += 1
                self.close()
                return None

    def capture(self) -> CameraFrame:
        frame = self.read()
        if frame is None:
            raise RuntimeError("USB webcam frame unavailable")
        return frame

    def health(self) -> str:
        return self._state  # passive: status polls never open/capture a physical device

    def close(self) -> None:
        with self._lock:
            if self._capture is not None:
                try:
                    self._capture.release()
                except Exception:
                    pass
                finally:
                    self._capture = None
                    if self._state in ("ONLINE", "NOT_VALIDATED"):
                        self._state = "NOT_CONNECTED"
