from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.ai.models import Identity
from app.behavior.models import Behavior
from app.behavior.fusion import SessionFusion, WeightSample, estimate_consumed
from app.behavior.temporal import Prediction, SessionSignal, SignalType, TemporalEngine
from app.main import create_app
from app.simulator.controller import (DailyState, FeedSensors, FeedState,
                                      SimulatedFeedController, SimulatedWaterController, WaterState)
from app.simulator.transport import SimulatedEsp32Transport
from app.simulator.persistence import SimulationSafetyStore
from app.storage.event_store import InMemoryEventStore
from app.storage.records import FeedingSession
from app.storage.repositories import RecordRepository
from tools.run_simulator import run
import pytest


def test_deterministic_feed_simulation_ack_loss_idempotency_and_history():
    device = SimulatedEsp32Transport()
    with TestClient(create_app(transport=device, store=InMemoryEventStore())) as client:
        key = {"Idempotency-Key": "synthetic-run-1"}
        first = client.post("/api/v1/feed/manual", headers=key).json()
        assert first["state"] == "PENDING" and device.received_feed_commands == 1
        assert client.post("/api/v1/feed/manual", headers=key).json() == first
        device.advance(seconds=0)
        device.online = False
        assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "PENDING"
        assert client.post("/api/v1/feed/manual", headers=key).json() == first
        assert device.received_feed_commands == 1
        device.online = True
        device.advance(seconds=1, weight_grams=10)
        device.advance(seconds=0.1, servo_closed=True)
        assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "SUCCESS"
        assert client.get(f"/api/v1/feed/manual/{first['request_id']}").json()["state"] == "SUCCESS"
        assert client.get("/api/v1/feeding-history").json()[0]["state"] == "SUCCESS"
        stored = client.get("/api/v1/sessions/feeding").json()[0]
        assert stored["source"] == "SOFTWARE_SIMULATOR" and stored["dispensed_grams"] is None
        assert device.feed.record.portions == 1


def test_food_empty_daily_limit_no_weight_progress_and_safe_reboot():
    sensor = FeedSensors(epoch_seconds=100000, date_key=20260930, rtc_valid=True,
                         food_available=True, scale_valid=True, servo_valid=True)
    feed = SimulatedFeedController()
    feed.tick(sensor)
    sensor.food_available = False
    feed.request(1, 10, sensor)
    assert feed.state == FeedState.REJECTED and feed.reason == "FOOD_EMPTY"
    sensor.food_available = True
    feed.record.portions = 4
    feed.request(2, 10, sensor)
    assert feed.reason == "DAILY_LIMIT_REJECTED"
    feed.record.portions = 0
    feed.request(3, 10, sensor)
    feed.tick(sensor)
    assert feed.servo_open
    record = feed.record
    feed.boot(record)
    assert feed.state == FeedState.SAFE_BOOT and not feed.servo_open
    feed.tick(sensor)
    assert feed.record.portions == 0
    feed.request(4, 10, sensor)
    assert feed.reason == "SAFE_BOOT"
    feed.boot(DailyState(date_key=sensor.date_key))  # synthetic operator clearance only
    feed.tick(sensor)
    feed.request(5, 10, sensor)
    feed.tick(sensor)
    sensor.monotonic_seconds = 5
    feed.tick(sensor)
    assert feed.reason == "NO_WEIGHT_PROGRESS" and not feed.servo_open


def test_water_simulation_hysteresis_progress_timeout_and_sensor_recovery():
    water = SimulatedWaterController()
    assert water.state == WaterState.SAFE_BOOT and not water.pump_on
    for t in range(3):
        water.tick(t, True, 80)
    water.tick(3, True, 20)
    assert not water.pump_on
    water.tick(4, True, 20)
    water.tick(5, True, 20)
    assert water.state == WaterState.FILLING and water.pump_on
    water.tick(10, True, 20)
    assert water.reason == "PUMP_NO_PROGRESS" and not water.pump_on
    water.boot()
    for t in range(3):
        water.tick(t, True, 80)
    water.tick(3, False, 20)
    assert water.state == WaterState.FAULT and not water.pump_on
    for t in range(3):
        water.tick(4 + t, True, 80)
    assert water.state == WaterState.NORMAL
    water.boot()
    for t in range(3):
        water.tick(t, True, 80)
    for t in range(3, 6):
        water.tick(t, True, 20, pump_valid=False)
    assert water.state == WaterState.FAULT and water.reason == "PUMP_FAULT" and not water.pump_on


def test_temporal_eating_occlusion_repeat_and_validated_fusion():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    engine = TemporalEngine()

    def p(t, behavior, confidence=0.9):
        return Prediction(timestamp=start + timedelta(seconds=t), monotonic_seconds=t,
                          identity=Identity.OWNER_CAT, behavior=behavior, confidence=confidence,
                          food_roi=True)

    assert engine.update(p(0, Behavior.NEAR_FOOD)) == []
    assert engine.update(p(1, Behavior.EATING)) == []
    began = engine.update(p(1.6, Behavior.EATING))[0]
    assert began.signal == SignalType.START and began.approach_delay_seconds == 1
    assert engine.update(p(2, Behavior.UNKNOWN, None)) == []
    assert engine.update(p(2.5, Behavior.EATING)) == []
    assert engine.update(p(3, Behavior.LEAVING)) == []
    ended = engine.update(p(4.1, Behavior.LEAVING))[0]
    assert ended.signal == SignalType.END and ended.duration_seconds == 1.5
    assert estimate_consumed(began, ended, [WeightSample(50, True, began.started_at)] * 3,
                             [WeightSample(40, True, ended.ended_at)] * 3) == 10
    assert estimate_consumed(began, ended, [WeightSample(50, False)] * 3,
                             [WeightSample(40, True)] * 3) is None
    engine.update(p(5, Behavior.EATING))
    repeat = engine.update(p(5.6, Behavior.EATING))[0]
    assert repeat.repeat_visits == 1


def test_temporal_drinking_and_unknown_do_not_infer_volume():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    engine = TemporalEngine()
    for t, kind, confidence in ((0, Behavior.NEAR_WATER, None), (1, Behavior.DRINKING, 0.9),
                                (1.6, Behavior.DRINKING, 0.9), (2, Behavior.UNKNOWN, None),
                                (2.5, Behavior.DRINKING, 0.9), (5, Behavior.LEAVING, None)):
        events = engine.update(Prediction(timestamp=now + timedelta(seconds=t),
                                         monotonic_seconds=t, identity=Identity.OWNER_CAT,
                                         behavior=kind, confidence=confidence, water_roi=True))
    assert events[0].signal == SignalType.END
    assert events[0].behavior == Behavior.DRINKING
    assert not hasattr(events[0], "water_consumed_grams")


def test_scenario_file_runs_software_only():
    for name in ("NORMAL", "FOOD_EMPTY", "DAILY_LIMIT_REJECTED", "SERIAL_DISCONNECT",
                 "SERIAL_RECOVERY", "OTHER_CAT", "NO_SUBJECT", "EATING", "DRINKING",
                 "WATER_LOW", "WATER_FILL_SUCCESS", "WATER_SENSOR_FAILURE", "PUMP_NO_PROGRESS"):
        result = run(name)
        assert result["label"] == "SIMULATION VERIFIED"
        if name in ("OTHER_CAT", "NO_SUBJECT"):
            assert result["feed_commands"] == 0
    assert run("NORMAL")["after"]["feeds"][0]["state"] == "SUCCESS"
    assert run("FOOD_EMPTY")["after"]["feeds"][0]["state"] == "REJECTED"


@pytest.mark.parametrize("scenario, expected", [
    ("NORMAL", "SUCCESS"), ("COOLDOWN_REJECTED", "REJECTED"),
    ("DAILY_LIMIT_REJECTED", "REJECTED"), ("FOOD_EMPTY", "REJECTED"),
    ("HX711_FAILURE", "REJECTED"), ("NO_WEIGHT_PROGRESS", "ERROR"),
    ("FEED_TIMEOUT", "ERROR"), ("RTC_INVALID", "REJECTED"),
    ("SERVO_FAILURE", "REJECTED"), ("SERIAL_DISCONNECT", "PENDING"),
    ("SERIAL_RECOVERY", "PENDING"),
])
def test_every_feeding_scenario_has_authoritative_simulated_outcome(scenario, expected):
    result = run(scenario)
    assert result["after"]["feeds"][0]["state"] == expected


@pytest.mark.parametrize("scenario, expected, pump", [
    ("WATER_NORMAL", "NORMAL", False), ("WATER_LOW", "FILLING", True),
    ("WATER_FILL_SUCCESS", "NORMAL", False), ("WATER_SENSOR_FAILURE", "FAULT", False),
    ("PUMP_NO_PROGRESS", "FAULT", False), ("PUMP_TIMEOUT", "FAULT", False),
])
def test_every_water_scenario_is_local_and_simulated(scenario, expected, pump):
    result = run(scenario)
    assert result["water_state"] == expected
    assert result["pump_simulated_on"] is pump
    assert result["after"]["sensors"] == "NOT_CONNECTED"


def test_offline_camera_does_not_crash_process_or_make_predictions():
    class OfflineCamera:
        def health(self):
            return "OFFLINE"

        def close(self):
            pass

    with TestClient(create_app(store=InMemoryEventStore(), camera=OfflineCamera())) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/status").json()["camera"] == "OFFLINE"
        assert client.get("/api/v1/behavior").json() == []


def test_reboot_restores_same_day_counters_and_corrupt_state_fails_closed(tmp_path):
    path = tmp_path / "synthetic-nvs.json"
    store = SimulationSafetyStore(path)
    saved = DailyState(date_key=20260930, portions=2, grams=60, last_feed_epoch=100000)
    store.save(saved)
    controller = SimulatedFeedController()
    controller.boot(store.load())
    sensor = FeedSensors(date_key=20260930, epoch_seconds=101000, rtc_valid=True,
                         food_available=True, scale_valid=True, servo_valid=True)
    controller.tick(sensor)
    assert controller.record.portions == 2 and not controller.servo_open
    interrupted = DailyState(date_key=sensor.date_key, portions=2, grams=60,
                             last_feed_epoch=100000, needs_inspection=True)
    store.save(interrupted)
    controller.boot(store.load())
    controller.tick(sensor)
    assert controller.state == FeedState.SAFE_BOOT
    assert controller.request(43, 10, sensor) and controller.reason == "SAFE_BOOT"
    assert controller.request(44, 10, sensor) and controller.reason == "SAFE_BOOT"
    store.save(saved)  # explicit synthetic operator clearance
    controller.boot(store.load())
    controller.tick(sensor)
    # Only a valid next-day clock clears the counters.
    sensor.date_key = 20261001
    sensor.rtc_valid = False
    controller.tick(sensor)
    assert controller.record.portions == 2
    sensor.rtc_valid = True
    controller.boot(store.load())
    controller.tick(sensor)
    assert controller.record.portions == 0
    path.write_text('{"invalid":true}', encoding="utf-8")
    controller.boot(store.load())
    controller.tick(sensor)
    assert controller.state == FeedState.SAFE_BOOT
    assert controller.request(45, 10, sensor) and controller.reason == "SAFE_BOOT"


def test_fusion_associates_only_matching_session_and_never_estimates_water():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo = RecordRepository(":memory:")
    feeding = FeedingSession(session_id="synthetic-feed", cat_identity=Identity.OWNER_CAT,
                             food_type="dry", requested_at=now, source="SYNTHETIC_TEST_DATA")
    start = SessionSignal(signal=SignalType.START, session_id="synthetic-visit",
                          identity=Identity.OWNER_CAT, behavior=Behavior.EATING,
                          started_at=now + timedelta(seconds=1))
    end = start.model_copy(update={"signal": SignalType.END,
                                    "ended_at": now + timedelta(seconds=6), "duration_seconds": 5})
    result = SessionFusion(repo).fuse(start, end, feeding=feeding,
                                      weight_before=[WeightSample(50, True, start.started_at)] * 3,
                                      weight_after=[WeightSample(40, True, end.ended_at)] * 3,
                                      source="SYNTHETIC_TEST_DATA")
    assert result.behavior.feeding_session_id == feeding.session_id
    assert result.estimated_food_consumed_grams == 10
    assert repo.get("behavior", "synthetic-visit").food_type == "dry"
    drinking_start = start.model_copy(update={"session_id": "synthetic-drink",
                                       "behavior": Behavior.DRINKING})
    drinking_end = end.model_copy(update={"session_id": "synthetic-drink",
                                   "behavior": Behavior.DRINKING})
    water = SessionFusion(repo).fuse(drinking_start, drinking_end, feeding=feeding,
                                    source="SYNTHETIC_TEST_DATA")
    assert water.drinking.duration_seconds == 5 and water.estimated_food_consumed_grams is None
    assert repo.get("drinking", "synthetic-drink").source == "SYNTHETIC_TEST_DATA"
    repo.close()
