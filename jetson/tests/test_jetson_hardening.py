"""Host-only synthetic Jetson-side controls, never physical camera/serial/GPU validation."""

import sqlite3
import gc
import tracemalloc
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.ai.budget import ProcessingBudget
from app.ai.interfaces import MockIdentityModel, MockBehaviorModel
from app.ai.models import Recognition, Identity
from app.ai.pipeline import ObservationPipeline
from app.ai.runtime import ExternalRuntimeAdapter, trusted_model_path
from app.ai.service import ObservationService
from app.behavior.models import Behavior, BehaviorObservation
from app.behavior.temporal import Prediction, TemporalEngine, SignalType
from app.camera.base import CameraFrame
from app.camera.frame_ops import limit_frame
from app.camera.settings import CaptureSettings
from app.camera.usb_webcam import UsbWebcamCameraProvider
from app.config import HardwareConfig
from app.main import create_app
from app.observability import WarningLimiter
from app.serial_link.mock_transport import MockEsp32Transport
from app.storage.event_store import InMemoryEventStore, Event as StoreEvent
from app.storage.records import BehaviorRecord, DrinkingSession
from app.storage.repositories import RecordRepository
from app.storage.summary import daily_summary
from app.vision.detector import CatDetection, DetectorIdentityModel
from app.vision.geometry import NormalizedBox
from tools.demo_replay import DemoCamera, DemoIdentityModel, DemoBehaviorModel, run_demo
from tools.list_cameras import list_devices
from tools.readiness_report import report as readiness_report
from tools.storage_report import tree_size


class Clock:
    value = 0.0
    def __call__(self):
        return self.value
    def sleep(self, seconds):
        self.value += seconds


@pytest.mark.parametrize("bad", ["../evil.onnx", "/etc/model.onnx", "C:\\evil.onnx", "file.txt", "sub/../../evil.pt"])
def test_model_paths_cannot_escape_trusted_configuration(tmp_path, bad):
    with pytest.raises(ValueError):
        trusted_model_path(tmp_path, bad)
    assert trusted_model_path(tmp_path, "identity.onnx") == tmp_path / "identity.onnx"


def test_roi_budget_threshold_and_shadow_configuration():
    settings = HardwareConfig.from_env({"CAMERA_PROVIDER": "VIDEO_REPLAY", "VIDEO_REPLAY_PATH": "clip.avi",
                    "ROI_FOOD_BOWL": "0.1,0.2,0.6,0.8", "IDENTITY_CONFIDENCE_THRESHOLD": "0.9"})
    assert settings.camera_provider == "VIDEO" and settings.ai_shadow_mode
    assert settings.food_roi.x1 == 0.1 and settings.identity_threshold == 0.9
    for env in ({"ROI_WATER_BOWL": "0,0,2,1"}, {"FRAME_QUEUE_DEPTH": "4"},
                {"AI_INFERENCE_FPS": "nan"}, {"DETECTOR_CONFIDENCE_THRESHOLD": "2"}):
        with pytest.raises(ValueError):
            HardwareConfig.from_env(env)


def test_optional_runtime_requires_configuration_and_never_imports_gpu(tmp_path):
    adapter = ExternalRuntimeAdapter("TENSORRT", tmp_path / "absent.engine", None)
    assert adapter.load() is False and adapter.health() == "NOT_CONFIGURED"
    with pytest.raises(RuntimeError):
        adapter.predict(CameraFrame(datetime.now(timezone.utc), bytes(12), 2, 2, True))
    adapter.close()


@pytest.mark.parametrize("boxes,expected", [
    ([], Identity.NO_SUBJECT), ([NormalizedBox(0, 0, 0.5, 1)], Identity.OWNER_CAT),
    ([NormalizedBox(0, 0, 0.5, 1), NormalizedBox(0.2, 0, 0.8, 1)], Identity.UNKNOWN),
    ([NormalizedBox(0.001, 0.001, 0.002, 0.002)], Identity.UNKNOWN),
])
def test_detector_crops_only_single_unambiguous_cat(boxes, expected):
    class Detector:
        def load(self): return True
        def predict(self, frame): return [CatDetection(box, 0.9) for box in boxes]
        def close(self): pass
    class Classifier:
        calls = 0
        def predict(self, frame):
            self.calls += 1
            assert frame.width < 8  # must receive crop, not the full scene
            return Recognition(timestamp=frame.captured_at, identity=Identity.OWNER_CAT, confidence=0.95)
    classifier = Classifier()
    model = DetectorIdentityModel(Detector(), classifier, 0.8, 0.8)
    assert model.load()
    frame = CameraFrame(datetime.now(timezone.utc), bytes(8 * 8 * 3), 8, 8, True)
    assert model.predict(frame).identity == expected
    assert classifier.calls == (1 if expected == Identity.OWNER_CAT else 0)
    model.close()


def test_low_detector_confidence_never_runs_identity_classifier():
    class Detector:
        def load(self): return True
        def predict(self, frame): return [CatDetection(NormalizedBox(0, 0, 0.5, 1), 0.2)]
        def close(self): pass
    class RejectClassifier:
        def predict(self, frame): raise AssertionError("unsafe full-frame/low-confidence classification")
    model = DetectorIdentityModel(Detector(), RejectClassifier(), 0.8, 0.8)
    model.load()
    frame = CameraFrame(datetime.now(timezone.utc), bytes(12), 2, 2, True)
    assert model.predict(frame).identity == Identity.UNKNOWN


@pytest.mark.parametrize("kind", [Behavior.EATING, Behavior.DRINKING])
def test_outside_bowl_roi_blocks_sessions_then_inside_confirms(kind):
    class IdentityModel(DemoIdentityModel):
        inside = False
        def predict(self, frame):
            return Recognition(timestamp=frame.captured_at, identity=Identity.OWNER_CAT, confidence=0.9,
               bounding_box=NormalizedBox(0.6, 0.6, 0.9, 0.9) if not self.inside else NormalizedBox(0.1, 0.1, 0.3, 0.3))
    class BehaviorModel:
        def predict(self, frame, identity):
            return BehaviorObservation(timestamp=frame.captured_at, identity=identity, behavior=kind,
                                       confidence=0.9, food_roi=True, water_roi=True)
    repo = RecordRepository(":memory:")
    identity = IdentityModel()
    pipeline = ObservationPipeline(DemoCamera(6), repo, identity, BehaviorModel(), replay_time=True,
                    food_roi=NormalizedBox(0, 0, 0.4, 0.4), water_roi=NormalizedBox(0, 0, 0.4, 0.4))
    for _ in range(3): pipeline.process_one_frame()
    assert pipeline.tracker.active is None
    identity.inside = True
    for _ in range(3): pipeline.process_one_frame()
    assert pipeline.tracker.active is not None
    pipeline.stop()
    assert repo.count("behavior") == 1
    repo.close()


def test_fast_source_slow_model_has_no_frame_backlog_and_skips_safely():
    clock = Clock()
    class SlowModel(DemoIdentityModel):
        def predict(self, frame):
            clock.sleep(0.2)  # synthetic slow inference, not real runtime benchmark
            return super().predict(frame)
    repo = RecordRepository(":memory:", max_rows=8)
    pipeline = ObservationPipeline(DemoCamera(100), repo, SlowModel(), DemoBehaviorModel(), clock=clock,
                   sleep=clock.sleep, replay_time=True, budget=ProcessingBudget(frame_skip=4))
    pipeline.run(max_frames=101)
    assert pipeline.processed == 25 and pipeline.skipped == 75
    assert len(pipeline.latencies) <= 256 and pipeline.status()["queue_depth"] == 1
    assert repo.count("behavior") <= 8
    repo.close()


def test_stale_live_frame_is_skipped_before_model_invocation():
    frame = CameraFrame(datetime.now(timezone.utc), bytes(12), 2, 2, True, monotonic_seconds=0)
    class Camera:
        def open(self): return True
        def read(self): return frame
        def close(self): pass
    class Model:
        def predict(self, frame): raise AssertionError("stale frame must not be classified")
    repo = RecordRepository(":memory:")
    pipeline = ObservationPipeline(Camera(), repo, Model(), clock=lambda: 10)
    assert pipeline.process_one_frame() == "SKIPPED"
    pipeline.stop(); repo.close()


def test_processing_resolution_is_bounded_without_hardware():
    frame = CameraFrame(datetime.now(timezone.utc), bytes(100 * 80 * 3), 100, 80, True)
    limited = limit_frame(frame, 50, 30)
    assert limited.width <= 50 and limited.height <= 30
    assert len(limited.pixels) == limited.width * limited.height * 3


def test_wall_clock_backward_jump_does_not_change_monotonic_duration():
    engine = TemporalEngine()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def predict(mono, wall, kind):
        return Prediction(timestamp=wall, monotonic_seconds=mono, identity=Identity.OWNER_CAT,
                          behavior=kind, confidence=0.9, food_roi=True)
    engine.update(predict(0, now, Behavior.EATING))
    engine.update(predict(0.6, now - timedelta(hours=1), Behavior.EATING))
    end = engine.update(predict(3, now - timedelta(hours=2), Behavior.LEAVING))[0]
    assert end.signal == SignalType.END and end.duration_seconds == 0.6
    assert end.ended_at == now + timedelta(seconds=0.6)


def test_import_lifespan_and_readiness_never_open_configured_physical_providers(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(UsbWebcamCameraProvider, "open", lambda self: calls.append("camera") or True)
    from app.serial_link.real_transport import RealEsp32SerialTransport
    monkeypatch.setattr(RealEsp32SerialTransport, "_connect", lambda self: calls.append("serial"))
    settings = HardwareConfig(camera_provider="USB", camera_device="/dev/explicit-test", esp32_transport="SERIAL",
                              esp32_serial_device="/dev/explicit-test")
    app = create_app(db_path=tmp_path / "idle.db", hardware=settings)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/readiness").json()["ready"] is False
    assert calls == []


def test_shadow_mode_has_no_automatic_feed_capability():
    app = create_app(store=InMemoryEventStore(), camera=DemoCamera(6), identity_model=DemoIdentityModel(),
                     behavior_model=DemoBehaviorModel(), hardware=HardwareConfig(camera_provider="VIDEO", video_file="test"))
    with TestClient(app) as client:
        app.state.pipeline.run(max_frames=7, interval=0.001)
        assert client.get("/api/v1/status").json()["ai"]["shadow_mode"] is True
        assert app.state.transport.feeds == {}
        assert app.state.pipeline.status()["automatic_feed_authorized"] is False


def test_sqlite_wal_timeout_atomicity_and_no_frame_level_writes(tmp_path):
    repo = RecordRepository(tmp_path / "wal.db", max_rows=8)
    assert repo.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert repo.connection.execute("PRAGMA busy_timeout").fetchone()[0] == 2000
    pipeline = ObservationPipeline(DemoCamera(50), repo, replay_time=True, sleep=lambda _: None)
    pipeline.run(max_frames=51)
    assert repo.count("behavior") == 0  # UNKNOWN mocks cause no per-frame rows
    assert repo.health() == "READY"
    repo.close()
    assert repo.health() == "NOT_AVAILABLE"


def test_storage_failure_faults_service_retains_one_write_and_health_lives(monkeypatch):
    app = create_app(store=InMemoryEventStore(), camera=DemoCamera(24), identity_model=DemoIdentityModel(),
               behavior_model=DemoBehaviorModel(), hardware=HardwareConfig(camera_provider="VIDEO", video_file="synthetic"))
    def failing(*args): raise sqlite3.OperationalError("synthetic disk failure")
    monkeypatch.setattr(app.state.records, "add_visit", failing)
    with TestClient(app) as client:
        service = app.state.observations
        service.pipeline.sleep = lambda _: None
        result = service.run(max_frames=100, max_failures=3)
        assert result["state"] == "FAULTED"
        assert result["pipeline"]["pending_writes"] == 1
        assert app.state.camera.index < 24
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/readiness").json()["ready"] is False
        assert app.state.transport.feeds == {}


def test_daily_summary_midnight_timezones_empty_and_unknown_consumption():
    repo = RecordRepository(":memory:")
    for i, start in enumerate((datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc),
                              datetime(2026, 1, 2, 1, 0, tzinfo=timezone(timedelta(hours=1))))):
        repo.add("behavior", BehaviorRecord(session_id=f"eat-{i}", cat_identity=Identity.OWNER_CAT,
                 behavior=Behavior.EATING, started_at=start, ended_at=start + timedelta(minutes=2),
                 duration_seconds=120, source="SYNTHETIC_TEST_DATA"))
        repo.add("drinking", DrinkingSession(session_id=f"drink-{i}", started_at=start, duration_seconds=5))
    first, second = daily_summary(repo, date(2026, 1, 1)), daily_summary(repo, date(2026, 1, 2))
    assert len(first["eating_times"]) == len(second["eating_times"]) == 1
    assert first["drinking_sessions"] == second["drinking_sessions"] == 1
    assert first["reliable_food_consumed_grams"] is None
    assert daily_summary(repo, date(2026, 1, 3))["eating_times"] == []
    repo.close()


def test_warning_rate_limiter_is_monotonic_and_bounded():
    clock = Clock()
    class Logger:
        messages = []
        def warning(self, message, extra): self.messages.append(message)
    logger = Logger()
    limiter = WarningLimiter(interval=10, max_keys=4, clock=clock)
    for _ in range(100): limiter.warn(logger, "camera", "camera failure", {})
    assert len(logger.messages) == 1
    clock.sleep(11); limiter.warn(logger, "camera", "camera failure", {})
    assert "suppressed 99" in logger.messages[-1]
    for i in range(20): limiter.warn(logger, str(i), "failure", {})
    assert len(limiter.entries) == 4


def test_passive_discovery_storage_and_readiness_tools(tmp_path):
    (tmp_path / "video0").write_bytes(b"synthetic node")
    devices = list_devices(tmp_path, tmp_path / "sys")
    assert devices[0]["opened"] is False
    assert tree_size(tmp_path, max_entries=1)["files"] == 1
    report = readiness_report(HardwareConfig())
    assert report["label"] == "NOT JETSON VERIFIED"
    assert report["sections"]["CAMERA"]["opened"] is False
    assert report["sections"]["AI_RUNTIME"]["model_loaded"] is False


def test_accelerated_hour_soak_bounds_records_buffers_and_pending_ids():
    from app.serial_link.link_manager import LinkManager
    from app.serial_link.protocol import Command
    repo = RecordRepository(":memory:", max_rows=8)
    pipeline = ObservationPipeline(DemoCamera(6000), repo, DemoIdentityModel(), DemoBehaviorModel(),
                     replay_time=True, source="SYNTHETIC_TEST_DATA", sleep=lambda _: None)
    pipeline.run(max_frames=6001, max_seconds=60)
    assert pipeline.frames == 6000  # 6000×0.6 s = one hour equivalent
    assert len(pipeline.latencies) == 256 and pipeline.status()["queue_depth"] == 1
    assert pipeline._pending_write is None and pipeline.tracker.active is None
    assert repo.count("behavior") <= 8 and repo.count("drinking") <= 8
    link = LinkManager(MockEsp32Transport(), max_pending=4)
    for i in range(1000):
        link.mark_pending(i); link.exchange(i, Command.PING); link.mark_done(i)
    assert link.pending == ()
    repo.close()


def test_serial_camera_rest_polling_concurrency_remains_responsive():
    entered, release = Event(), Event()
    class SlowModel(DemoIdentityModel):
        def predict(self, frame):
            entered.set()
            assert release.wait(3), "test must release controlled model"
            return super().predict(frame)
    device = MockEsp32Transport()
    app = create_app(store=InMemoryEventStore(), camera=DemoCamera(24), identity_model=SlowModel(),
                behavior_model=DemoBehaviorModel(), transport=device,
                hardware=HardwareConfig(camera_provider="VIDEO", video_file="synthetic"))
    with TestClient(app) as client:
        app.state.observations.start_background(max_frames=3, interval=0.001)
        try:
            assert entered.wait(2)
            for online in (True, False, True):
                device.online = online
                assert client.get("/api/v1/health").status_code == 200
                assert client.get("/api/v1/status").json()["esp32_online"] is online
            assert device.feeds == {}
        finally:
            release.set()
            assert app.state.observations.stop(timeout=3)
        assert not app.state.observations.status()["worker_alive"]


def test_synthetic_demo_labels_results_as_non_real():
    result = run_demo()
    assert result["label"] == "SYNTHETIC DEMO" and result["automatic_actions"] == []
    assert any(x["behavior"] == "EATING" for x in result["sessions"])
    assert any(x["behavior"] == "DRINKING" for x in result["sessions"])
    assert result["status"]["failures"] >= 2


def test_roi_dropout_tolerance_ends_at_last_observed_frame():
    from jetson.tests.test_observation_pipeline import SyntheticCamera, SyntheticBehaviorModel
    class ROIModel:
        def predict(self, frame):
            box = NormalizedBox(0.6, 0.6, 0.9, 0.9) if frame.pixels[0] == 2 else NormalizedBox(0.1, 0.1, 0.3, 0.3)
            return Recognition(timestamp=frame.captured_at, identity=Identity.OWNER_CAT,
                               confidence=0.9, bounding_box=box)
    repo = RecordRepository(":memory:")
    pipeline = ObservationPipeline(SyntheticCamera([0, 0.6, 0.9, 1.2, 3]), repo, ROIModel(),
                   SyntheticBehaviorModel([Behavior.EATING] * 4 + [Behavior.LEAVING]), replay_time=True,
                   food_roi=NormalizedBox(0, 0, 0.4, 0.4))
    pipeline.run(max_frames=6, interval=0.001)
    record = repo.list("behavior")[0]
    assert record.duration_seconds == 1.2 and repo.count("behavior") == 1
    repo.close()


def test_transient_storage_error_retries_same_single_completed_visit(monkeypatch):
    repo = RecordRepository(":memory:")
    real_write = repo.add_visit
    failures = [True, True]
    def flaky(*args):
        if failures:
            failures.pop()
            raise sqlite3.OperationalError("synthetic busy database")
        return real_write(*args)
    monkeypatch.setattr(repo, "add_visit", flaky)
    pipeline = ObservationPipeline(DemoCamera(6), repo, DemoIdentityModel(), DemoBehaviorModel(), replay_time=True)
    outcomes = [pipeline.process_one_frame() for _ in range(6)]
    assert outcomes[-1] == "STORAGE_FAILURE" and pipeline.status()["pending_writes"] == 1
    assert pipeline.process_one_frame() == "STORAGE_FAILURE"
    assert pipeline.process_one_frame() == "EOF"
    assert repo.count("behavior") == 1 and pipeline.status()["pending_writes"] == 0
    pipeline.stop(); repo.close()


def test_cleanup_attempts_all_resources_even_when_camera_close_raises():
    class Camera(DemoCamera):
        def close(self): raise RuntimeError("synthetic close error")
    class Model(DemoIdentityModel):
        loaded = closed = False
        def load(self): self.loaded = True; return True
        def close(self): self.closed = True
    class BehaviorModel(DemoBehaviorModel):
        closed = False
        def close(self): self.closed = True
    identity, behavior = Model(), BehaviorModel()
    repo = RecordRepository(":memory:")
    pipeline = ObservationPipeline(Camera(2), repo, identity, behavior, replay_time=True)
    assert pipeline.start() and identity.loaded
    pipeline.stop()
    assert identity.closed and behavior.closed and not pipeline.running
    repo.close()


def test_camera_backend_factory_timeout_configuration_is_explicit():
    calls = []
    class Capture:
        def isOpened(self): return True
        def set(self, key, value): calls.append((key, value)); return False
        def get(self, key): return {3: 640, 4: 480, 5: 10}.get(key, 0)
        def release(self): pass
    def factory(device, backend):
        calls.append((device, backend))
        return Capture()
    camera = UsbWebcamCameraProvider("/dev/test", factory, CaptureSettings(backend="V4L2"))
    assert camera.health() == "NOT_CONNECTED" and calls == []
    assert camera.open() and calls[0] == ("/dev/test", 200)
    assert not camera.timeout_supported
    camera.close()
    settings = CaptureSettings(backend="GSTREAMER", pipeline="v4l2src device=/dev/test ! appsink max-buffers=1 drop=true")
    gst = UsbWebcamCameraProvider(None, factory, settings)
    assert gst.open() and (settings.pipeline, 1800) in calls
    gst.close()


def test_python_heap_state_after_warmup_has_no_obvious_frame_accumulation():
    repo = RecordRepository(":memory:", max_rows=8)
    pipeline = ObservationPipeline(DemoCamera(2000), repo, DemoIdentityModel(), DemoBehaviorModel(), replay_time=True)
    for _ in range(300): pipeline.process_one_frame()
    tracemalloc.start()
    gc.collect()
    before, _ = tracemalloc.get_traced_memory()
    for _ in range(1500): pipeline.process_one_frame()
    gc.collect()
    after, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert after - before < 6_000_000  # Python heap sanity bound, not native/GPU leak validation
    assert len(pipeline.latencies) == 256 and repo.count("behavior") <= 8
    assert len(pipeline.tracker.approach) <= 4 and len(pipeline.tracker.last_end) <= 4
    pipeline.stop(); repo.close()


def test_failed_second_model_load_closes_partial_first_runtime():
    class First(MockIdentityModel):
        closed = False
        def close(self): self.closed = True
    class Second(MockBehaviorModel):
        def load(self): return False
    first = First()
    repo = RecordRepository(":memory:")
    camera = DemoCamera()
    pipeline = ObservationPipeline(camera, repo, first, Second())
    assert pipeline.start() is False and first.closed
    assert camera.index == 0
    pipeline.stop(); repo.close()


def test_replay_deliberate_restart_has_new_namespace_and_monotonic_epoch():
    repo = RecordRepository(":memory:")
    pipeline = ObservationPipeline(DemoCamera(6), repo, DemoIdentityModel(), DemoBehaviorModel(), replay_time=True)
    pipeline.run(max_frames=7, interval=0.001)
    pipeline.camera = DemoCamera(6)
    pipeline.run(max_frames=7, interval=0.001)
    assert repo.count("behavior") == 2
    assert len({row.session_id for row in repo.list("behavior")}) == 2
    repo.close()


def test_capture_pipeline_does_not_allow_automatic_recording_sink():
    with pytest.raises(ValueError, match="recording"):
        CaptureSettings(backend="GSTREAMER", pipeline="v4l2src ! tee ! filesink location=private.avi ! appsink")


def test_serial_backoff_is_monotonic_and_repeated_polls_do_not_delay_recovery(monkeypatch):
    from app.serial_link.real_transport import RealEsp32SerialTransport
    from app.serial_link.protocol import Frame, Command, encode, decode
    from jetson.tests.test_real_transport import FakePort
    clock = Clock()
    monkeypatch.setattr("app.serial_link.real_transport.time.monotonic", clock)
    calls = []
    def factory(**kwargs):
        calls.append(clock())
        if len(calls) == 1:
            raise OSError("synthetic unplug")
        return FakePort(**kwargs)
    link = RealEsp32SerialTransport("synthetic", startup_delay=0, serial_factory=factory,
                                   reconnect_backoff_seconds=2)
    request = encode(Frame(1, Command.PING))
    with pytest.raises(ConnectionError): link.exchange(request)
    clock.sleep(1)
    with pytest.raises(ConnectionError): link.exchange(request)
    assert calls == [0]
    clock.sleep(1.1)
    assert decode(link.exchange(request)).command == Command.ACK
    assert len(calls) == 2
    link.close()


def test_daily_summary_counts_pending_attempt_without_claiming_dispense():
    app = create_app(store=InMemoryEventStore())
    with TestClient(app) as client:
        assert client.post("/api/v1/feed/manual").json()["state"] == "PENDING"
        report = client.get("/api/v1/daily-summary").json()
        assert report["feeding_requests"] == 1 and report["feeding_sessions"] == 0
        assert report["reliable_food_consumed_grams"] is None
        assert client.get("/api/v1/daily-summary?day=9999-12-31").status_code == 422
