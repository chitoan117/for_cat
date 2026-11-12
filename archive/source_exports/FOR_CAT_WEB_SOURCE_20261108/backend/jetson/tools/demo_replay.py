"""SYNTHETIC DEMO assets/models, tool-only: never camera footage or real AI."""

import json
from datetime import datetime, timedelta, timezone

from app.ai.models import Identity, Recognition
from app.ai.pipeline import ObservationPipeline
from app.behavior.models import Behavior, BehaviorObservation
from app.camera.base import CameraFrame
from app.storage.repositories import RecordRepository


class DemoCamera:
    def __init__(self, count=24, failures=False):
        self.count, self.failures = count, failures
        self.index = 0
        self.eof = False

    def open(self):
        return not self.eof

    def read(self):
        if self.index >= self.count:
            self.eof = True
            return None
        index = self.index
        self.index += 1
        if self.failures and index % 24 == 19:
            return None
        return CameraFrame(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index * 0.6),
                           bytes([index % 24]) * (16 * 16 * 3), 16, 16, True, media_seconds=index * 0.6)

    def close(self):
        pass

    def health(self):
        return "MOCK"


class DemoIdentityModel:
    label = "SYNTHETIC DEMO / SYNTHETIC_TEST_MODEL"

    def __init__(self, failures=False):
        self.failures = failures

    def predict(self, frame):
        index = frame.pixels[0]
        if self.failures and index == 18:
            raise RuntimeError("synthetic model failure")
        identity = Identity.OWNER_CAT if index < 12 else Identity.OTHER_CAT if index < 18 else Identity.UNKNOWN
        return Recognition(timestamp=frame.captured_at, identity=identity,
                           confidence=0.9 if identity != Identity.UNKNOWN else None)


class DemoBehaviorModel:
    label = "SYNTHETIC DEMO / SYNTHETIC_TEST_MODEL"

    def predict(self, frame, identity):
        index = frame.pixels[0]
        kind = (Behavior.EATING if index in (0, 1, 2, 12, 13, 14) else
                Behavior.DRINKING if index in (6, 7, 8) else Behavior.LEAVING)
        return BehaviorObservation(timestamp=frame.captured_at, identity=identity, behavior=kind,
                                   confidence=0.9, food_roi=kind == Behavior.EATING, water_roi=kind == Behavior.DRINKING)


def run_demo():
    repo = RecordRepository(":memory:")
    try:
        pipeline = ObservationPipeline(DemoCamera(failures=True), repo, DemoIdentityModel(failures=True),
                    DemoBehaviorModel(), replay_time=True, source="SYNTHETIC_DEMO", sleep=lambda _: None)
        status = pipeline.run(max_frames=25)
        return {"label": "SYNTHETIC DEMO", "status": status,
                "sessions": [r.model_dump(mode="json") for r in repo.list("behavior")],
                "automatic_actions": [], "real_ai_verified": False}
    finally:
        repo.close()


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
