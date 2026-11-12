"""Optional OpenCV file replay; synthetic/offline tests can inject a capture factory."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Callable

from app.camera.base import CameraFrame, CameraProvider


class VideoFileCameraProvider(CameraProvider):
    @property
    def eof(self) -> bool:
        return self._ended

    def __init__(self, path: str, capture_factory: Callable | None = None):
        if not path:
            raise ValueError("video path required")
        self.path = Path(path)
        self._factory = capture_factory
        self._capture = None
        self._lock = RLock()
        self._start = datetime.now(timezone.utc)
        self._frame_count = 0
        self._ended = False

    def open(self) -> bool:
        with self._lock:
            if self._capture is not None:
                return True
            if self._ended or not self.path.is_file():
                return False
            if self._factory is None:
                try:
                    import cv2
                except ImportError:
                    return False
                self._factory = cv2.VideoCapture
            try:
                self._capture = self._factory(str(self.path))
                if not self._capture.isOpened():
                    self.close()
                    return False
                self._start = datetime.now(timezone.utc)
                self._frame_count = 0
                return True
            except Exception:
                self.close()
                return False

    def read(self) -> CameraFrame | None:
        with self._lock:
            if not self.open():
                return None
            try:
                ok, image = self._capture.read()
                if not ok or image is None:
                    self._ended = True
                    self.close()
                    return None
                # POS_MSEC tracks presentation time; fall back to frame count/FPS.
                position = float(self._capture.get(0))  # cv2.CAP_PROP_POS_MSEC == 0
                fps = float(self._capture.get(5))  # cv2.CAP_PROP_FPS == 5
                seconds = position / 1000 if position > 0 else self._frame_count / fps if fps > 0 else 0
                self._frame_count += 1
                height, width = image.shape[:2]
                return CameraFrame(self._start + timedelta(seconds=seconds), image.tobytes(),
                                   width, height, False, "BGR", media_seconds=seconds)
            except Exception:
                self.close()
                return None

    def capture(self) -> CameraFrame:
        frame = self.read()
        if frame is None:
            raise EOFError("video replay finished or unavailable")
        return frame

    def health(self) -> str:
        # Opening doesn't consume a frame; EOF is reported on read.
        return "MOCK" if self.open() else "OFFLINE"

    def close(self) -> None:
        with self._lock:
            if self._capture is not None:
                try:
                    self._capture.release()
                finally:
                    self._capture = None

    def reset(self) -> None:
        self.close()
        self._ended = False
