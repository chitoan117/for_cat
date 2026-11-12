import io
import json

import pytest

from bringup.sensor_monitor import Lines, collect, parse_report


def report(**changes):
    row = {"mode": "diag_all_sensors", "monotonic_ms": 1000, "hardware_verified": False,
           "actuator_outputs_enabled": 0, "physical_pump_on": False, "would_request_pump": False,
           "rtc_type": "DS1302", "rtc_health": "NOT_CONNECTED", "weight_health": "NOT_CALIBRATED",
           "food_health": "NOT_CONFIGURED", "water_health": "NOT_CONFIGURED",
           "raw_counts": 1234, "grams": None, "food_distance_cm": None, "water_distance_cm": None,
           "food_percent": None, "water_percent": None}
    row.update(changes)
    return json.dumps(row).encode("ascii")


def test_unknown_weight_and_levels_stay_null():
    data = parse_report(report())
    assert data["grams"] is None and data["food_percent"] is None and data["hardware_verified"] is False


def test_actual_device_numbers_preserved_without_awarding_verification():
    data = parse_report(report(grams=10.25, food_distance_cm=25, food_percent=42.5))
    assert data["grams"] == 10.25 and data["food_percent"] == 42.5 and data["hardware_verified"] is False


@pytest.mark.parametrize("change", [
    {"actuator_outputs_enabled": 1}, {"physical_pump_on": True}, {"hardware_verified": True},
    {"monotonic_ms": True}, {"monotonic_ms": -1}, {"rtc_type": "DS3231"},
    {"grams": float("nan")}, {"food_percent": 101}, {"water_distance_cm": 0},
    {"weight_health": "GUESS"}, {"grams": True}, {"actuator_outputs_enabled": False},
])
def test_bad_or_enabled_diagnostic_reports_rejected(change):
    with pytest.raises(ValueError):
        parse_report(report(**change))


def test_duplicate_json_and_oversized_report_rejected():
    with pytest.raises(ValueError):
        parse_report(b'{"mode":"diag_all_sensors","mode":"diag_rtc"}')
    with pytest.raises(ValueError):
        parse_report(b"x" * 4097)


def test_line_budget_recovers_after_oversized_input_and_crlf():
    decoder = Lines()
    for _ in range(65):
        assert decoder.feed(b"x" * 64) == []
    assert decoder.oversized == 1 and len(decoder.buffer) <= 4096
    assert decoder.feed(b"\r\nOK\r\n") == [b"OK"]
    with pytest.raises(ValueError):
        decoder.feed(b"x" * 65)


def test_monitor_never_sends_commands_or_opens_database():
    class Port:
        def __init__(self):
            self.pending = b"BOOT\r\n" + report() + b"\r\n"

        def read(self, count):
            part, self.pending = self.pending[:count], self.pending[count:]
            return part

        def write(self, _):
            pytest.fail("read-only monitor attempted a command")

    ticks = iter(n / 20 for n in range(100))
    output = io.StringIO()
    result = collect(Port(), 2, output, clock=lambda: next(ticks))
    assert result["accepted_reports"] == 1 and result["serial_commands_sent"] == 0
    assert json.loads(output.getvalue())["report"]["grams"] is None
    assert result["physical_validation_automatically_awarded"] is False


def test_zero_and_nan_capture_duration_rejected_before_reading():
    for duration in (0, -1, float("nan"), 3601):
        with pytest.raises(ValueError):
            collect(None, duration, io.StringIO())
