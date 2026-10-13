"""Scenario-file driven, deterministic end-to-end SOFTWARE simulation."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.ai.models import Identity
from app.behavior.models import Behavior
from app.behavior.temporal import Prediction, TemporalEngine
from app.main import create_app
from app.simulator.transport import SimulatedEsp32Transport
from app.storage.event_store import InMemoryEventStore

SCENARIOS = Path(__file__).resolve().parents[1] / "app" / "simulator" / "scenarios.json"


def run(name: str) -> dict:
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    if name not in scenarios:
        raise ValueError(f"unknown scenario: {name}")
    settings = scenarios[name]
    device = SimulatedEsp32Transport()
    feed_mode = settings.get("feed")
    if feed_mode == "cooldown":
        device.feed.record.last_feed_epoch = device.sensors.epoch_seconds
    if feed_mode == "daily_limit":
        device.feed.record.portions = 4
    if feed_mode == "food_empty":
        device.sensors.food_available = False
    if feed_mode == "hx711_failure":
        device.sensors.scale_valid = False
    if feed_mode == "rtc_invalid":
        device.sensors.rtc_valid = False
    if feed_mode == "servo_failure":
        device.sensors.servo_valid = False
    identity = Identity(settings["identity"])
    signals = []
    behavior = settings.get("behavior")
    if behavior:
        engine = TemporalEngine()
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        kind = Behavior(behavior)
        for t in (0, 0.6, 1.2, 3):
            predicted = kind if t < 3 else Behavior.LEAVING
            signals.extend(engine.update(Prediction(
                timestamp=now + timedelta(seconds=t), monotonic_seconds=t,
                identity=identity, behavior=predicted, confidence=0.9 if t < 3 else None,
                food_roi=kind == Behavior.EATING, water_roi=kind == Behavior.DRINKING,
            )))
    water_mode = settings.get("water")
    if water_mode:
        water = device.water
        for t in range(3):
            water.tick(t, True, 80)
        if water_mode != "normal":
            for t in range(3, 6):
                water.tick(t, True, 20)
        if water_mode == "success":
            water.tick(6, True, 80)
        elif water_mode == "sensor_failure":
            water.tick(6, False, 20)
        elif water_mode == "no_progress":
            water.tick(11, True, 20)
        elif water_mode == "timeout":
            for t in (10, 14, 18, 22, 26, 30, 35):
                water.tick(t, True, min(60, 20 + 2 * (t - 5)))
    with TestClient(create_app(transport=device, store=InMemoryEventStore())) as client:
        before = client.get("/api/v1/status").json()
        request = None
        if identity == Identity.OWNER_CAT and feed_mode:
            request = client.post("/api/v1/feed/manual", headers={"Idempotency-Key": "simulation-request"}).json()
            if feed_mode in ("success", "disconnect", "recovery", "no_progress", "timeout"):
                device.advance(seconds=0)
                if feed_mode == "success":
                    device.advance(seconds=1, weight_grams=10)
                    device.advance(seconds=0.1, servo_closed=True)
                elif feed_mode == "no_progress":
                    device.advance(seconds=5)
                elif feed_mode == "timeout":
                    for t in (4, 8, 12, 16, 20):
                        device.advance(seconds=4, weight_grams=t * 0.5)
                elif feed_mode in ("disconnect", "recovery"):
                    device.online = False
            if feed_mode == "recovery":
                client.get("/api/v1/status")
                device.online = True
        after = client.get("/api/v1/status").json()
        history = client.get("/api/v1/feeding-history").json()
    return {"label": "SIMULATION VERIFIED", "scenario": name, "before": before,
            "request": request, "after": after, "feed_state": device.feed.state,
            "feed_reason": device.feed.reason, "feed_commands": device.received_feed_commands,
            "water_state": device.water.state if water_mode else None,
            "pump_simulated_on": device.water.pump_on if water_mode else None,
            "signals": [signal.model_dump(mode="json") for signal in signals],
            "feeding_history": history}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=sorted(json.loads(SCENARIOS.read_text(encoding="utf-8"))))
    args = parser.parse_args()
    print(json.dumps(run(args.scenario), indent=2, default=str))
