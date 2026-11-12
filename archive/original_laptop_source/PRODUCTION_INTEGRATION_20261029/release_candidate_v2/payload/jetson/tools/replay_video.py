"""Bounded video replay through mock models or supplied predictions; no inference."""

import argparse
import json
from pathlib import Path

from app.ai.interfaces import MockBehaviorModel, MockIdentityModel
from app.behavior.temporal import Prediction, TemporalEngine
from app.camera.video_file import VideoFileCameraProvider
from app.config import HardwareConfig


def replay(video: str, *, predictions: list[dict] | None = None,
           max_frames: int = 300, provider: VideoFileCameraProvider | None = None) -> dict:
    if not 1 <= max_frames <= 1000:
        raise ValueError("max_frames must be between 1 and 1000")
    camera = provider or VideoFileCameraProvider(video)
    if not camera.open():
        return {"status": "VIDEO_NOT_AVAILABLE", "frames": 0}
    identity_model, behavior_model = MockIdentityModel(), MockBehaviorModel()
    settings = HardwareConfig.from_env()
    engine = TemporalEngine(settings.behavior_confirm_frames, settings.behavior_confirm_seconds)
    signals, frames = [], 0
    first_time = None
    try:
        while frames < max_frames:
            frame = camera.read()
            if frame is None:
                break
            if first_time is None:
                first_time = frame.captured_at
            elapsed = max(0.0, (frame.captured_at - first_time).total_seconds())
            if predictions is None or frames >= len(predictions):
                identity = identity_model.predict(frame)
                behavior = behavior_model.predict(frame, identity.identity)
                values = {"identity": identity.identity, "behavior": behavior.behavior,
                          "confidence": None, "food_roi": False, "water_roi": False}
            else:
                values = predictions[frames]
            signals.extend(engine.update(Prediction(timestamp=frame.captured_at,
                                                     monotonic_seconds=elapsed, **values)))
            frames += 1
        if frames:
            signals.extend(engine.flush(elapsed + engine.dropout_seconds))
    finally:
        camera.close()
    return {"status": "REPLAY_ONLY_NO_AI_VALIDATION", "frames": frames,
            "signals": [s.model_dump(mode="json") for s in signals]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="local recorded file, not a live camera")
    parser.add_argument("--predictions", type=Path, help="optional explicit predictions JSON array")
    parser.add_argument("--max-frames", type=int, default=300)
    args = parser.parse_args()
    values = None
    try:
        if args.predictions:
            if not args.predictions.is_file() or args.predictions.stat().st_size > 1_000_000:
                raise ValueError("predictions missing or exceed 1 MB")
            values = json.loads(args.predictions.read_text(encoding="utf-8"))
            if not isinstance(values, list):
                raise ValueError("predictions must be an array")
        print(json.dumps(replay(args.video, predictions=values, max_frames=args.max_frames), indent=2))
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f"REPLAY_FAILED: {exc}\n")
