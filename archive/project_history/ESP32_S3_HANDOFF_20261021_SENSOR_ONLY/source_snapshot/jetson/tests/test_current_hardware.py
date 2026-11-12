"""Current role/pin contract and receiver regressions, never physical evidence."""
import json
from pathlib import Path
import re

import pytest

from bringup.sensor_monitor import parse_report

ROOT = Path(__file__).resolve().parents[2]


def test_machine_contract_matches_cpp_and_keeps_inventory_unassigned():
    config = json.loads((ROOT / "config/hardware_current.json").read_text())
    header = (ROOT / "esp32/include/current_hardware.h").read_text()
    for name, pin in config["pins"].items():
        match = re.search(r"\b" + name.upper() + r"\s*=\s*(UNASSIGNED|\d+)", header)
        assert match is not None, name
        assert (None if match[1] == "UNASSIGNED" else int(match[1])) == pin
    assigned = [p for p in config["pins"].values() if p is not None]
    assert len(assigned) == len(set(assigned)) == 15
    assert config["actuator_outputs_enabled"] == 0
    assert config["automatic_feed_authorized"] is False
    assert config["hx711"]["installed"] is None
    assert config["eating_model_required_now"] is False


def current_report(**changes):
    data = {
        "mode": "diag_all_sensors", "monotonic_ms": 1000, "hardware_verified": False,
        "actuator_outputs_enabled": 0, "physical_pump_on": False, "would_request_pump": False,
        "rtc_type": "DS1302", "rtc_health": "NOT_CONNECTED", "weight_health": "NOT_CONFIGURED",
        "food_health": "NOT_CONFIGURED", "water_health": "NOT_CONFIGURED",
        "raw_counts": None, "grams": None, "food_distance_cm": None,
        "water_distance_cm": None, "food_percent": None, "water_percent": None,
        "telemetry_schema_version": 2, "pin_contract": "2026-10-21", "hx711_installed": False,
        "weight": {"installed": False, "valid": False, "quality": "NOT_INSTALLED",
                   "value_grams": None, "sampled_at_ms": None, "calibration_version": 1, "calibration_id": None},
        "consumed_grams": None, "approach_health": "NOT_CALIBRATED", "approach_distance_cm": 24.5,
        "approach_echo_ack": True, "food_echo_ack": False,
        "distance_roles": {"channel_1": "APPROACH", "channel_2": "WATER_OPERATIONAL"},
        "motion_input_configured": True, "motion": True,
        "food_reservoir_percent": None, "water_reservoir_percent": None,
    }
    data.update(changes)
    return json.dumps(data).encode("ascii")


def test_approach_is_not_food_level_and_pir_is_only_observation():
    row = parse_report(current_report())
    assert row["approach_distance_cm"] == 24.5 and row["food_distance_cm"] is None
    assert row["food_percent"] is None and row["motion"] is True
    assert row["physical_pump_on"] is False and row["hardware_verified"] is False


@pytest.mark.parametrize("changes", [
    {"distance_roles": {"channel_1": "FOOD", "channel_2": "WATER"}},
    {"food_percent": 40}, {"food_distance_cm": 25}, {"water_reservoir_percent": 60},
    {"approach_distance_cm": True}, {"approach_health": "ASSUMED"},
    {"motion_input_configured": False}, {"food_echo_ack": True},
])
def test_current_receiver_rejects_role_confusion_or_invented_inventory(changes):
    with pytest.raises(ValueError):
        parse_report(current_report(**changes))
