"""SYNTHETIC_TEST_MODEL fixtures only: no real AI predictions or camera access."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai.models import Identity, Recognition
from app.behavior.models import Behavior, BehaviorObservation
from app.behavior.fusion import WeightSample
from app.camera.base import CameraFrame
from app.config import HardwareConfig
from app.main import create_app
from app.serial_link.mock_transport import MockEsp32Transport
from app.storage.event_store import InMemoryEventStore
from app.storage.records import FeedingSession


class SyntheticCamera:
    def __init__(self, times):
        self.times = times
        self.index = 0
        self.eof = False
        self.closed = False

    def open(self):
        return not self.eof

    def read(self):
        if self.index == len(self.times):
            self.eof = True
            return None
        index = self.index
        self.index += 1
        return CameraFrame(datetime(2026, 1, 1, tzinfo=timezone.utc) +
                           timedelta(seconds=self.times[index]), bytes([index]) * 12, 2, 2, True)

    def close(self):
        self.closed = True

    def health(self):
        return "MOCK" if not self.closed else "OFFLINE"


class SyntheticIdentityModel:
    label = "SYNTHETIC_TEST_MODEL"

    def __init__(self, identity=Identity.OWNER_CAT, fail_at=None):
        self.identity, self.fail_at = identity, fail_at

    def predict(self, frame):
        if frame.pixels[0] == self.fail_at:
            raise RuntimeError("SYNTHETIC_TEST_MODEL failure")
        return Recognition(timestamp=frame.captured_at, identity=self.identity, confidence=0.9)


class SyntheticBehaviorModel:
    label = "SYNTHETIC_TEST_MODEL"

    def __init__(self, behaviors):
        self.behaviors = behaviors

    def predict(self, frame, identity):
        behavior = self.behaviors[frame.pixels[0]]
        return BehaviorObservation(timestamp=frame.captured_at, identity=identity,
                                   behavior=behavior, confidence=None if behavior == Behavior.UNKNOWN else 0.9,
                                   food_roi=behavior == Behavior.EATING, water_roi=behavior == Behavior.DRINKING)


def app_for(camera, kind, identity=Identity.OWNER_CAT, fail_at=None, db=None):
    return create_app(db_path=db, store=InMemoryEventStore() if db is None else None,
                      camera=camera, identity_model=SyntheticIdentityModel(identity, fail_at),
                      behavior_model=SyntheticBehaviorModel(kind), pipeline_source="SYNTHETIC_TEST_MODEL",
                      transport=MockEsp32Transport(),
                      hardware=HardwareConfig(camera_provider="VIDEO", video_file="synthetic-fixture"))


@pytest.mark.parametrize("kind,route,typed", [
    (Behavior.EATING, "feeding-history", "behavior"),
    (Behavior.DRINKING, "drinking-history", "drinking"),
])
def test_predictions_temporal_storage_and_api_agree(kind, route, typed, tmp_path):
    camera = SyntheticCamera([0, 0.6, 1.2, 3])
    app = app_for(camera, [kind, kind, kind, Behavior.LEAVING], db=tmp_path / "canonical.db")
    with TestClient(app) as client:
        for _ in range(4):
            assert app.state.pipeline.process_one_frame() == "PROCESSED"
        behavior = client.get("/api/v1/behavior").json()
        history = client.get(f"/api/v1/{route}").json()
        assert len(behavior) == len(history) == 1
        assert behavior[0]["details"]["cat_identity"] == "OWNER_CAT"
        assert history[0]["details"]["duration_seconds"] == 1.2
        assert history[0]["details"]["source"] == "SYNTHETIC_TEST_MODEL"
        assert app.state.records.count(typed) == 1
        assert app.state.store.list() == []  # read projections, not duplicate writes
        assert app.state.transport.feeds == {}
        assert client.get("/api/v1/status").json()["ai"]["trained_model_validated"] is False
        daily = client.get("/api/v1/daily-summary?day=2026-01-01").json()
        assert len(daily["eating_times"] if kind == Behavior.EATING else daily["drinking_times"]) == 1
        assert daily["reliable_food_consumed_grams"] is None
        for _ in range(2):
            assert len(client.get(f"/api/v1/{route}").json()) == 1


@pytest.mark.parametrize("identity", [Identity.OTHER_CAT, Identity.UNKNOWN])
def test_identity_never_authorizes_automatic_feed(identity):
    app = app_for(SyntheticCamera([0, 0.6, 2.5]), [Behavior.EATING] * 3, identity)
    with TestClient(app) as client:
        app.state.pipeline.run(max_frames=4, interval=0.001)
        assert app.state.transport.feeds == {}
        if identity == Identity.UNKNOWN:
            assert client.get("/api/v1/feeding-history").json() == []
        else:
            assert client.get("/api/v1/feeding-history").json()[0]["details"]["cat_identity"] == "OTHER_CAT"


def test_dropout_eof_closes_at_last_positive_frame_without_extra_duration():
    app = app_for(SyntheticCamera([0, 0.6, 0.9, 1.2]),
                  [Behavior.EATING, Behavior.EATING, Behavior.UNKNOWN, Behavior.EATING])
    with TestClient(app) as client:
        result = app.state.pipeline.run(max_frames=6, interval=0.001)
        assert result["sessions"] == 1
        event = client.get("/api/v1/feeding-history").json()[0]
        assert event["details"]["duration_seconds"] == 1.2
        assert event["details"]["completion_reason"] == "EOF"
        assert app.state.camera.closed
        assert client.get("/api/v1/status").json()["camera"] == "OFFLINE"


def test_model_exception_degrades_ai_but_health_lives():
    app = app_for(SyntheticCamera([0, 0.6]), [Behavior.EATING] * 2, fail_at=1)
    with TestClient(app) as client:
        assert app.state.pipeline.process_one_frame() == "PROCESSED"
        assert app.state.pipeline.process_one_frame() == "MODEL_FAILURE"
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/status").json()["ai"]["state"] == "DEGRADED"
        assert app.state.transport.feeds == {}
        assert client.get("/api/v1/behavior").json() == []


def test_default_mock_models_do_not_fabricate_observations():
    app = create_app(store=InMemoryEventStore(), camera=SyntheticCamera([0, 0.6, 2]))
    with TestClient(app) as client:
        app.state.pipeline.run(max_frames=4, interval=0.001)
        assert client.get("/api/v1/status").json()["ai"]["state"] == "MOCK"
        assert client.get("/api/v1/behavior").json() == []


def test_failure_loop_is_bounded_and_not_busy_looping():
    class OfflineCamera(SyntheticCamera):
        def open(self):
            return False

    app = create_app(store=InMemoryEventStore(), camera=OfflineCamera([]))
    with TestClient(app):
        sleeps = []
        app.state.pipeline.sleep = lambda seconds: sleeps.append(seconds)
        result = app.state.pipeline.run(max_frames=100, max_failures=3)
        assert result["camera"] == "OFFLINE"
        assert len(sleeps) == 2 and not result["running"]


def test_controlled_loop_stop_and_canonical_retry_are_idempotent():
    app = app_for(SyntheticCamera([0, 0.6, 1.2, 2]), [Behavior.DRINKING] * 4)
    with TestClient(app) as client:
        pipeline = app.state.pipeline
        result = pipeline.run(max_frames=20, interval=0.001, stop_when=lambda: pipeline.frames >= 3)
        assert result["frames"] == 3 and result["sessions"] == 1
        record = app.state.records.list("behavior")[0]
        drinking = app.state.records.list("drinking")[0]
        assert app.state.records.add_visit(record, drinking) is False
        pipeline.stop()
        assert len(client.get("/api/v1/drinking-history").json()) == 1
        assert app.state.records.count("drinking") == 1


def test_observation_survives_sqlite_reopen_without_duplicate_history(tmp_path):
    path = tmp_path / "observations.db"
    app = app_for(SyntheticCamera([0, 0.6, 1.2]), [Behavior.DRINKING] * 3, db=path)
    with TestClient(app) as client:
        app.state.pipeline.run(max_frames=4, interval=0.001)
        first = client.get("/api/v1/drinking-history").json()
    with TestClient(create_app(db_path=path)) as client:
        assert client.get("/api/v1/drinking-history").json() == first
        assert len(client.get("/api/v1/behavior").json()) == 1


def test_injected_fusion_context_exposes_only_validated_synthetic_consumption():
    app = app_for(SyntheticCamera([0, 0.6, 1.2, 3]),
                  [Behavior.EATING, Behavior.EATING, Behavior.EATING, Behavior.LEAVING])
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feeding = FeedingSession(session_id="synthetic-dispense", cat_identity=Identity.OWNER_CAT,
                             food_type="dry", requested_at=now, source="SYNTHETIC_TEST_DATA")
    app.state.pipeline.fusion_context = lambda start, end: {
        "feeding": feeding, "weight_before": [WeightSample(50, True, start.started_at)] * 3,
        "weight_after": [WeightSample(40, True, end.ended_at)] * 3}
    with TestClient(app) as client:
        app.state.pipeline.run(max_frames=5, interval=0.001)
        details = client.get("/api/v1/feeding-history").json()[0]["details"]
        assert details["feeding_session_id"] == "synthetic-dispense"
        assert details["estimated_consumed_grams"] == 10
        assert details["source"] == "SYNTHETIC_TEST_MODEL"
        assert app.state.transport.feeds == {}
