"""Explicit read-only ASCII sensor monitor (Python 3.6+), NOT binary UART v1."""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from .weight_contract import validate_weight

MODES = {"diag_current_hardware", "diag_all_sensors", "diag_hx711", "diag_rtc", "diag_i2c",
         "diag_food_sensor", "diag_approach_sensor", "diag_water_sensor", "diag_oled_button_buzzer"}
HEALTH = {"NOT_CONFIGURED", "NOT_CONNECTED", "NOT_CALIBRATED", "INITIALIZING",
          "HEALTHY", "DEGRADED", "FAULT"}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate sensor JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("non-finite JSON constant: " + value)


def parse_report(line):
    if not isinstance(line, bytes) or not 1 <= len(line) <= 4096:
        raise ValueError("sensor line must be bounded bytes")
    try:
        data = json.loads(line.decode("ascii"), object_pairs_hook=_object, parse_constant=_invalid_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("invalid sensor encoding/nesting") from exc
    if not isinstance(data, dict) or not isinstance(data.get("mode"), str) or data["mode"] not in MODES:
        raise ValueError("not a known sensor diagnostic report")
    if (data.get("hardware_verified") is not False or
            type(data.get("actuator_outputs_enabled")) is not int or data["actuator_outputs_enabled"] != 0 or
            data.get("physical_pump_on") is not False or type(data.get("would_request_pump")) is not bool):
        raise ValueError("report does not match disabled-actuator diagnostic contract")
    if type(data.get("monotonic_ms")) is not int or not 0 <= data["monotonic_ms"] <= 0xffffffff:
        raise ValueError("invalid device milliseconds")
    for key in ("rtc_health", "weight_health", "food_health", "water_health"):
        if not isinstance(data.get(key), str) or data[key] not in HEALTH:
            raise ValueError("invalid sensor health")
    if data.get("rtc_type") != "DS1302":
        raise ValueError("this monitor expects the current DS1302 firmware")
    for key in ("raw_counts", "grams", "food_distance_cm", "water_distance_cm", "food_percent", "water_percent"):
        if key not in data:
            raise ValueError("missing sensor measurement")
        value = data[key]
        if value is not None:
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError("invalid sensor number")
            if key.endswith("percent") and not 0 <= value <= 100:
                raise ValueError("invalid sensor percentage")
            if key.endswith("distance_cm") and value <= 0:
                raise ValueError("invalid sensor distance")
    if "telemetry_schema_version" in data:
        if type(data["telemetry_schema_version"]) is not int or data["telemetry_schema_version"] not in (1, 2):
            raise ValueError("unsupported diagnostic telemetry schema")
        weight = validate_weight(data)
        if data.get("hx711_installed") is not weight["installed"]:
            raise ValueError("weight installation flags disagree")
        if not weight["installed"] and (data.get("grams") is not None or data.get("raw_counts") is not None):
            raise ValueError("uninstalled HX711 produced a reading")
        if data.get("grams") != weight["value_grams"]:
            raise ValueError("legacy/versioned weight values disagree")
        if data["telemetry_schema_version"] == 2:
            if data.get("pin_contract") != "2026-10-21" or data.get("distance_roles") != {
                    "channel_1": "APPROACH", "channel_2": "WATER_OPERATIONAL"}:
                raise ValueError("wrong current distance roles")
            if data.get("approach_health") not in HEALTH or type(data.get("approach_echo_ack")) is not bool:
                raise ValueError("invalid approach health/acknowledgment")
            distance = data.get("approach_distance_cm")
            if distance is not None and (type(distance) not in (float, int) or not math.isfinite(distance) or distance <= 0):
                raise ValueError("invalid approach distance")
            if type(data.get("motion_input_configured")) is not bool or (
                    type(data.get("motion")) is not bool if data["motion_input_configured"] else data.get("motion") is not None):
                raise ValueError("invalid PIR input availability")
            if any(data.get(key) is not None for key in (
                    "food_distance_cm", "food_percent", "food_reservoir_percent", "water_reservoir_percent")):
                raise ValueError("TBD inventory sensors cannot produce measurements")
            if data.get("food_health") != "NOT_CONFIGURED" or data.get("food_echo_ack") is not False:
                raise ValueError("approach was mislabeled as food inventory")
            if data["mode"] == "diag_current_hardware":
                current = data.get("current_hardware")
                if not isinstance(current, dict) or current.get("food_reservoir_sensor") != "NOT_WIRED" or \
                        current.get("water_reservoir_sensor") != "NOT_WIRED":
                    raise ValueError("unwired reservoir reported as installed")
                if current.get("auto_feed") is not False or current.get("auto_water") is not False or \
                        current.get("servo_armed") is not False or current.get("pump_armed") is not False or \
                        current.get("servo_state") != "PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED" or \
                        current.get("pump_state") != "OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED":
                    raise ValueError("unsafe combined diagnostic actuator state")
                if current.get("oled_address") != "0x3c" or type(current.get("oled_initialized")) is not bool or \
                        type(current.get("rtc_detected")) is not bool or type(current.get("weight_calibrated")) is not bool:
                    raise ValueError("invalid current OLED/RTC/HX status")
                if current["rtc_detected"] != (data["rtc_health"] == "HEALTHY") or \
                        current["oled_initialized"] != (data.get("oled_health") == "HEALTHY"):
                    raise ValueError("device health and current status disagree")
                for key in ("approach_timeout_count", "operational_water_timeout_count",
                            "pir_transition_count", "weight_window_samples"):
                    if type(current.get(key)) is not int or not 0 <= current[key] <= 0xffffffff:
                        raise ValueError("invalid diagnostic counter: " + key)
                if current["weight_window_samples"] > 4:
                    raise ValueError("invalid weight window")
                for key in ("approach_distance_valid", "operational_water_distance_valid"):
                    if type(current.get(key)) is not bool:
                        raise ValueError("invalid distance validity")
                if current["approach_distance_valid"] != (data.get("approach_distance_cm") is not None) or \
                        current["operational_water_distance_valid"] != (data.get("water_distance_cm") is not None):
                    raise ValueError("distance validity and values disagree")
                stamp = current.get("pir_last_transition_ms")
                if stamp is not None and (type(stamp) is not int or not 0 <= stamp <= 0xffffffff):
                    raise ValueError("invalid PIR transition timestamp")
                if (current["pir_transition_count"] == 0) != (stamp is None):
                    raise ValueError("invalid PIR transition absence")
                threshold = current.get("weight_stability_threshold_grams")
                if threshold is not None and (type(threshold) not in (float, int) or
                                              not math.isfinite(threshold) or not 0 < threshold <= 10):
                    raise ValueError("invalid weight stability threshold")
                spread = current.get("weight_window_range_grams")
                if spread is not None and (type(spread) not in (float, int) or
                                           not math.isfinite(spread) or spread < 0):
                    raise ValueError("invalid weight window spread")
                if (spread is None) != (current["weight_window_samples"] < 4):
                    raise ValueError("missing or fabricated weight spread")
                stable = current.get("weight_stable")
                if stable is not None and (type(stable) is not bool or threshold is None or spread is None or
                                           stable != (spread <= threshold)):
                    raise ValueError("invalid weight stability evidence")
    # Legacy reports can be observed, never promoted to validated weight evidence.
    return data


class Lines:
    def __init__(self):
        self.buffer = bytearray()
        self.discard = False
        self.oversized = 0

    def feed(self, chunk):
        if not isinstance(chunk, bytes) or len(chunk) > 64:
            raise ValueError("serial backend exceeded bounded read")
        result = []
        for byte in chunk:
            if byte in (10, 13):
                if self.buffer and not self.discard:
                    result.append(bytes(self.buffer))
                self.buffer.clear()
                self.discard = False
            elif not self.discard:
                if len(self.buffer) >= 4096:
                    self.buffer.clear()
                    self.discard = True
                    self.oversized += 1
                else:
                    self.buffer.append(byte)
        return result


def collect(port, seconds, stream, clock=time.monotonic):
    if not math.isfinite(seconds) or not 0 < seconds <= 3600:
        raise ValueError("duration must be finite, 0..3600 seconds")
    decoder = Lines()
    deadline = clock() + seconds
    accepted = rejected = 0
    while clock() < deadline:
        for line in decoder.feed(port.read(64)):
            if not line.startswith(b"{"):
                continue  # boot banner / human diagnostic replies, not sensor samples
            try:
                report = parse_report(line)
            except (ValueError, TypeError, OverflowError):
                rejected += 1
                continue
            record = {"received_utc": datetime.now(timezone.utc).isoformat(),
                      "source": "ESP32_SENSOR_DIAGNOSTIC", "report": report}
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            accepted += 1
    return {"accepted_reports": accepted, "rejected_reports": rejected,
            "oversized_lines": decoder.oversized, "serial_commands_sent": 0,
            "physical_validation_automatically_awarded": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 3600:
        parser.error("seconds must be finite and <=3600")
    stream = None
    try:
        import serial
        stream = args.output.open("x", encoding="utf-8") if args.output else sys.stdout
        # Set modem signals before opening; some bridges can still reset on open.
        with serial.Serial(port=None, baudrate=115200, timeout=0.1) as port:
            port.dtr = False
            port.rts = False
            port.port = args.device
            port.open()
            result = collect(port, args.seconds, stream)
        print(json.dumps(result), file=sys.stderr)
        return 0 if result["accepted_reports"] > 0 and result["rejected_reports"] == 0 and result["oversized_lines"] == 0 else 2
    except (OSError, ValueError, ImportError) as exc:
        print("SENSOR_MONITOR_ERROR: " + str(exc), file=sys.stderr)
        return 2
    finally:
        if stream is not None and stream is not sys.stdout:
            stream.close()


if __name__ == "__main__":
    raise SystemExit(main())
