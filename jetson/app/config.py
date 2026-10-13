"""Phase 2 device selection; default remains completely mocked."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse
from math import isfinite

from app.camera.settings import CaptureSettings
from app.vision.geometry import NormalizedBox
from app.ai.runtime import trusted_model_path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "events.db"
MAX_EVENTS = 1000
MAX_PAYLOAD = 256


@dataclass(frozen=True)
class HardwareConfig:
    camera_provider: str = "MOCK"
    camera_device: str | int | None = None
    esp32_transport: str = "MOCK"
    esp32_serial_device: str | None = None
    video_file: str | None = None
    serial_baud: int = 115200
    db_path: str = str(DATA_PATH)
    max_events: int = MAX_EVENTS
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: tuple[str, ...] = ()
    behavior_confirm_frames: int = 2
    behavior_confirm_seconds: float = 0.5
    preference_min_sessions: int = 3
    capture: CaptureSettings = CaptureSettings()
    inference_fps: float = 2
    max_processing_width: int = 640
    max_processing_height: int = 480
    frame_skip: int = 1
    queue_depth: int = 1
    max_frame_age_seconds: float = 1
    ai_runtime: str = "MOCK"
    model_root: Path = Path(__file__).resolve().parents[2] / "ai" / "models"
    identity_model_path: Path | None = None
    behavior_model_path: Path | None = None
    detector_model_path: Path | None = None
    identity_threshold: float | None = None
    behavior_threshold: float | None = None
    detector_threshold: float | None = None
    food_roi: NormalizedBox | None = None
    water_roi: NormalizedBox | None = None
    approach_roi: NormalizedBox | None = None
    ai_shadow_mode: bool = True
    log_level: str = "INFO"
    serial_reconnect_backoff_seconds: float = 2

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "HardwareConfig":
        env = os.environ if environ is None else environ
        camera = env.get("CAMERA_PROVIDER", "MOCK").upper()
        esp32 = env.get("ESP32_TRANSPORT", "MOCK").upper()
        if camera == "VIDEO_REPLAY":
            camera = "VIDEO"
        if camera not in ("MOCK", "USB", "VIDEO"):
            raise ValueError("CAMERA_PROVIDER must be MOCK, USB or VIDEO")
        if esp32 not in ("MOCK", "SERIAL"):
            raise ValueError("ESP32_TRANSPORT must be MOCK or SERIAL")
        raw_camera_device = env.get("CAMERA_DEVICE") or None
        camera_device = int(raw_camera_device) if raw_camera_device and raw_camera_device.isdecimal() else raw_camera_device
        serial_device = env.get("ESP32_SERIAL_DEVICE") or None
        video_file = env.get("VIDEO_REPLAY_PATH") or None
        if camera == "USB" and camera_device is None and env.get("CAMERA_BACKEND", "AUTO").upper() != "GSTREAMER":
            raise ValueError("CAMERA_DEVICE is required for USB camera mode")
        if camera == "USB" and isinstance(camera_device, int) and camera_device > 16:
            raise ValueError("CAMERA_DEVICE index must be <=16")
        if esp32 == "SERIAL" and not serial_device:
            raise ValueError("ESP32_SERIAL_DEVICE is required for SERIAL transport mode")
        if camera == "VIDEO" and not video_file:
            raise ValueError("VIDEO_REPLAY_PATH is required for VIDEO camera mode")
        baud = int(env.get("ESP32_SERIAL_BAUD", "115200"))
        if baud != 115200:
            raise ValueError("protocol v1 requires ESP32_SERIAL_BAUD=115200")
        db_path = env.get("DATABASE_PATH") or str(DATA_PATH)
        retention = int(env.get("EVENT_RETENTION", str(MAX_EVENTS)))
        port = int(env.get("API_PORT", "8000"))
        frames = int(env.get("BEHAVIOR_CONFIRM_FRAMES", "2"))
        seconds = float(env.get("BEHAVIOR_CONFIRM_SECONDS", "0.5"))
        sessions = int(env.get("PREFERENCE_MIN_SESSIONS", "3"))
        if not 1 <= retention <= 100000 or not 1 <= port <= 65535 or not 2 <= frames <= 30:
            raise ValueError("invalid retention, port or behavior frame count")
        if not 0 <= seconds <= 30 or not 2 <= sessions <= 100:
            raise ValueError("invalid behavior or preference threshold")
        origins = tuple(x.strip() for x in env.get("CORS_ORIGINS", "").split(",") if x.strip())
        for origin in origins:
            parsed = urlparse(origin)
            if (origin == "*" or parsed.scheme not in ("http", "https") or not parsed.netloc
                    or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        capture = CaptureSettings(width=int(env.get("CAMERA_WIDTH", "640")), height=int(env.get("CAMERA_HEIGHT", "480")),
                  fps=float(env.get("CAMERA_FPS", "10")), backend=env.get("CAMERA_BACKEND", "AUTO").upper(),
                  pipeline=env.get("CAMERA_GSTREAMER_PIPELINE") or None,
                  read_timeout_ms=int(env.get("CAMERA_READ_TIMEOUT_MS", "1000")),
                  failure_threshold=int(env.get("CAMERA_FAILURE_THRESHOLD", "3")))
        fps = float(env.get("AI_INFERENCE_FPS", "2"))
        width, height = int(env.get("PROCESSING_MAX_WIDTH", "640")), int(env.get("PROCESSING_MAX_HEIGHT", "480"))
        skip, queue = int(env.get("FRAME_SKIP", "1")), int(env.get("FRAME_QUEUE_DEPTH", "1"))
        age = float(env.get("MAX_FRAME_AGE_SECONDS", "1"))
        if not isfinite(fps) or not 0 < fps <= 30 or not 1 <= width <= 1920 or not 1 <= height <= 1080 or \
                not 1 <= skip <= 60 or queue != 1 or not isfinite(age) or not 0 < age <= 30:
            raise ValueError("invalid processing budget; queue depth must be 1")
        runtime = env.get("AI_RUNTIME", "MOCK").upper()
        if runtime not in ("MOCK", "ONNX", "TENSORRT"):
            raise ValueError("AI_RUNTIME must be MOCK, ONNX or TENSORRT")
        root = Path(env.get("MODEL_ROOT") or str(cls.model_root))
        paths = {name: trusted_model_path(root, env.get(name.upper() + "_MODEL_PATH"))
                 for name in ("identity", "behavior", "detector")}
        def threshold(name):
            raw = env.get(name.upper() + "_CONFIDENCE_THRESHOLD")
            value = float(raw) if raw else None
            if value is not None and (not isfinite(value) or not 0 <= value <= 1):
                raise ValueError("confidence threshold must be 0..1 or unconfigured")
            return value
        shadow = env.get("AI_SHADOW_MODE", "true").lower()
        if shadow not in ("true", "false"):
            raise ValueError("AI_SHADOW_MODE must be true/false")
        level = env.get("LOG_LEVEL", "INFO").upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError("invalid LOG_LEVEL")
        backoff = float(env.get("SERIAL_RECONNECT_BACKOFF_SECONDS", "2"))
        if not isfinite(backoff) or not 0.25 <= backoff <= 30:
            raise ValueError("invalid serial reconnect backoff")
        return cls(camera, camera_device, esp32, serial_device, video_file, baud,
                   db_path, retention, env.get("API_HOST", "127.0.0.1"), port,
                   origins, frames, seconds, sessions, capture=capture, inference_fps=fps,
                   max_processing_width=width, max_processing_height=height, frame_skip=skip,
                   queue_depth=queue, max_frame_age_seconds=age, ai_runtime=runtime, model_root=root,
                   identity_model_path=paths["identity"], behavior_model_path=paths["behavior"],
                   detector_model_path=paths["detector"], identity_threshold=threshold("identity"),
                   behavior_threshold=threshold("behavior"), detector_threshold=threshold("detector"),
                   food_roi=NormalizedBox.parse(env.get("ROI_FOOD_BOWL")),
                   water_roi=NormalizedBox.parse(env.get("ROI_WATER_BOWL")),
                   approach_roi=NormalizedBox.parse(env.get("ROI_FEEDER_APPROACH")),
                   ai_shadow_mode=shadow == "true", log_level=level,
                   serial_reconnect_backoff_seconds=backoff)
