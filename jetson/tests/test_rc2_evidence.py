"""SYNTHETIC_TEST_DATA: no live sensors, real AI, or physical serial link."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.analytics.preference import PreferencePolicy, trend
from app.ai.models import Identity
from app.behavior.models import Behavior
from app.behavior.fusion import WeightSample, estimate_consumed
from app.behavior.temporal import SessionSignal, SignalType
from app.behavior.temporal import Prediction, TemporalEngine
from app.main import create_app
from app.serial_link.protocol import Command, Frame, decode, encode
from app.simulator.transport import SimulatedEsp32Transport
from app.simulator.controller import FeedState, WaterState, SimulatedWaterController
from app.storage.records import FeedingSession


@pytest.mark.parametrize("before,after,added,expected", [
    ([50, 50.1, 50], [40, 40.1, 40], False, 10),
    ([50, 53, 50], [40, 40, 40], False, None),
    ([50, 50, 50], [51, 51, 51], False, None),
    ([50, 50, 50], [], False, None),
    ([50, 50, 50], [40, 40, 40], True, None),
])
def test_consumption_requires_unambiguous_stable_pre_post_readings(before, after, added, expected):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    start = SessionSignal(signal=SignalType.START, session_id="synthetic-eat", identity=Identity.OWNER_CAT,
                          behavior=Behavior.EATING, started_at=now)
    end = start.model_copy(update={"signal": SignalType.END, "ended_at": now + timedelta(seconds=10)})
    consumed = estimate_consumed(start, end, [WeightSample(x, True, now) for x in before],
                                 [WeightSample(x, True, end.ended_at) for x in after], food_added_during_session=added)
    assert consumed == expected
    assert estimate_consumed(start, end, [WeightSample(50, False)] * 3,
                             [WeightSample(40, True)] * 3) is None


def test_multiple_food_preference_threshold_weights_and_evidence():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = [FeedingSession(session_id=f"{food}-{i}", requested_at=now, food_type=food, cat_identity=Identity.OWNER_CAT,
                             result="SUCCESS", source="SYNTHETIC_TEST_DATA", dispensed_grams=20,
                             estimated_consumed_grams=consumed, approach_delay_seconds=delay,
                             repeat_visits=repeat, eating_started_at=now,
                             eating_finished_at=now + timedelta(seconds=20))
               for food, consumed, delay, repeat in (("food-a", 18, 10, 1), ("food-b", 4, 100, 0))
               for i in range(4)]
    policy = PreferencePolicy(allow_synthetic_test_data=True, min_sessions=3)
    assert trend("food-a", records[:1], policy)["status"] == "INSUFFICIENT_DATA"
    a, b = trend("food-a", records, policy), trend("food-b", records, policy)
    assert a["sessions"] == b["sessions"] == 4
    assert a["preference_trend"] == "HIGH" and b["preference_trend"] == "LOW"
    assert a["evidence"]["consumption_ratio_mean"] == 0.9
    assert a["evidence"]["eating_duration_mean_seconds"] == 20
    assert "leftover_mean_grams" in b["evidence"] and "consumption_ratio_stddev" in a["evidence"]
    changed = trend("food-a", records, PreferencePolicy(allow_synthetic_test_data=True,
                      consumption_weight=1, approach_weight=0, repeat_weight=0))
    assert changed["evidence"]["experimental_score"] == 0.9


@pytest.mark.parametrize("terminal", [False, True])
def test_sqlite_restart_retry_never_resends_accepted_command(tmp_path, terminal):
    path = tmp_path / "restart.db"
    device = SimulatedEsp32Transport()
    header = {"Idempotency-Key": "synthetic-original"}
    with TestClient(create_app(db_path=path, transport=device)) as client:
        result = client.post("/api/v1/feed/manual", headers=header).json()
        device.advance(seconds=0)
        if terminal:
            device.advance(seconds=1, weight_grams=10)
            device.advance(seconds=0.1, servo_closed=True)
            client.get("/api/v1/status")
    device.online = False
    with TestClient(create_app(db_path=path, transport=device)) as client:
        retry = client.post("/api/v1/feed/manual", headers=header).json()
        assert retry["request_id"] == result["request_id"]
        assert retry["state"] == ("SUCCESS" if terminal else "PENDING")
        assert client.get("/api/v1/health").status_code == 200
        assert device.received_feed_commands == 1
        device.online = True
        for _ in range(2):
            client.get("/api/v1/status")
        assert device.received_feed_commands == 1
        assert client.app.state.records.count("feeding") == (1 if terminal else 0)


def test_stale_final_status_does_not_turn_pending_request_into_success(tmp_path):
    class StaleResponse(SimulatedEsp32Transport):
        def exchange(self, request):
            frame = decode(request)
            if frame.command == Command.FEED_STATUS:
                return encode(Frame(frame.request_id + 1, Command.FEED_STATUS, b"\x01"))
            return super().exchange(request)

    device = StaleResponse()
    with TestClient(create_app(db_path=tmp_path / "stale.db", transport=device)) as client:
        result = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "key"}).json()
        for _ in range(2):
            assert client.get("/api/v1/status").json()["feeds"][0]["state"] == "PENDING"
        assert client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "key"}).json() == result
        assert device.received_feed_commands == 1


def test_sensor_change_after_request_and_pump_fault_fail_closed():
    device = SimulatedEsp32Transport()
    device.feed.request(1, 10, device.sensors)
    device.sensors.food_available = False
    device.advance(seconds=0)
    assert device.feed.state == FeedState.FAULT and not device.feed.servo_open
    water = SimulatedWaterController()
    for t in range(5):
        water.tick(t, True, 20)
    assert water.pump_on
    water.tick(6, True, 20, pump_valid=False)
    assert water.state == WaterState.FAULT and not water.pump_on


def test_unobserved_long_gap_is_not_counted_as_continuous_eating():
    tracker = TemporalEngine()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def eating(t):
        return Prediction(timestamp=now + timedelta(seconds=t), monotonic_seconds=t,
                          identity=Identity.OWNER_CAT, behavior=Behavior.EATING, confidence=0.9, food_roi=True)
    tracker.update(eating(0))
    assert tracker.update(eating(0.6))[0].signal == SignalType.START
    ended = tracker.update(eating(10))[0]
    assert ended.signal == SignalType.END and ended.duration_seconds == 0.6


def test_api_never_exposes_raw_actuator_gpio_intents(tmp_path):
    app = create_app(db_path=tmp_path / "safe-api.db")
    paths = app.openapi()["paths"]
    assert not any(term in path for path in paths for term in ("/servo", "/pump", "/gpio"))
    with TestClient(app) as client:
        for raw in ("/servo/open", "/pump/on", "/gpio/write"):
            assert client.post("/api/v1" + raw).status_code == 404


def test_disconnect_during_result_poll_reports_offline_not_success(tmp_path):
    class VanishingLink(SimulatedEsp32Transport):
        def exchange(self, request):
            if decode(request).command == Command.FEED_STATUS:
                raise ConnectionError("synthetic unplug after heartbeat")
            return super().exchange(request)

    device = VanishingLink()
    with TestClient(create_app(db_path=tmp_path / "vanished.db", transport=device)) as client:
        request = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "one"}).json()
        state = client.get("/api/v1/status").json()
        assert state["esp32_online"] is False and state["link_state"] == "OFFLINE"
        assert state["feeds"][0]["state"] == "PENDING"
        assert client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "one"}).json() == request
        assert device.received_feed_commands == 1
