"""Run actual firmware-loop cases + Jetson report parser with host-only IO (3.6+)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jetson"))
from bringup.sensor_monitor import parse_report

CASES = ("boot_missing", "calibration_flow", "independent_echoes",
         "faults_and_recovery", "clock_and_parser", "reserved_pins_and_pir")


def require(value, message):
    if not value:
        raise ValueError(message)


def run_matrix(binary, output):
    binary = Path(binary).resolve()
    output = Path(output).resolve()
    require(binary.is_file(), "firmware-loop binary missing")
    require(output.parent.is_dir(), "output parent must exist")
    output.mkdir()  # new run only; never silently overwrite earlier evidence
    summary = {"scope": "SYNTHETIC_FIRMWARE_LOOP", "result": "RUNNING", "named_cases": 0,
               "cpp_assertions": 0, "decoded_firmware_reports": 0,
               "physical_hardware_used": False, "flashed": False, "cases": []}
    try:
        for name in CASES:
            serial_log = output / (name + ".serial.log")
            completed = subprocess.run([str(binary), name, str(serial_log)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       universal_newlines=True, timeout=30)
            (output / (name + ".execution.log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
            require(completed.returncode == 0, "firmware loop failed: " + name + ": " + completed.stderr)
            record = json.loads(completed.stdout)
            require(record.get("case") == name and record.get("scope") == "SYNTHETIC_FIRMWARE_LOOP"
                    and record.get("result") == "PASS" and record.get("actuator_gpio_touches") == 0,
                    "invalid firmware-loop test result")
            require(type(record.get("assertions")) is int and record["assertions"] > 0,
                    "missing C++ assertion count")
            reports = [parse_report(line) for line in serial_log.read_bytes().splitlines() if line.startswith(b"{")]
            require(reports, "no firmware JSON reached the actual Jetson parser: " + name)
            require(all(row["mode"] == "diag_all_sensors" for row in reports), "unexpected firmware profile")
            if name == "boot_missing":
                require(all(row["grams"] is None and row["rtc_epoch"] is None and
                            row["food_percent"] is None and row["water_percent"] is None for row in reports),
                        "missing sensors produced invented measurements")
            elif name == "calibration_flow":
                require(any(row["grams"] == 25 for row in reports), "calibrated weight not serialized/received")
                require(any(row["grams"] is None for row in reports), "timeout/tare null weight not serialized/received")
            elif name == "independent_echoes":
                require(any(row["approach_distance_cm"] is not None and row["water_percent"] is not None and
                            row["approach_echo_ack"] and row["water_echo_ack"] and row["food_percent"] is None for row in reports),
                        "approach/operational-water roles not received")
            elif name == "faults_and_recovery":
                require(any(row["water_health"] == "NOT_CONNECTED" and row["approach_distance_cm"] is not None for row in reports),
                        "fault isolation not visible to receiver")
                require(any(row["water_health"] == "FAULT" and row["water_distance_cm"] is None for row in reports),
                        "stuck echo not visible to receiver")
            elif name == "clock_and_parser":
                require(any(row["rtc_reason"] == "CLOCK_HALTED" and row["rtc_epoch"] is None for row in reports),
                        "halted clock not visible to receiver")
                require(any(row["rtc_utc"] == "2026-10-17T12:34:56Z" for row in reports),
                        "explicit synthetic RTC readback not received")
            elif name == "reserved_pins_and_pir":
                require(any(row["motion"] is True for row in reports) and any(row["motion"] is False for row in reports),
                        "PIR transitions not received")
                require(b"REJECTED LEGACY_FOOD_CHANNEL" in serial_log.read_bytes(), "stale channel command accepted")
            with (output / (name + ".reports.jsonl")).open("x", encoding="utf-8") as stream:
                for row in reports:
                    stream.write(json.dumps({"scope": "SYNTHETIC_FIRMWARE_LOOP", "case": name,
                                             "device_report": row}, allow_nan=False) + "\n")
            record["decoded_firmware_reports"] = len(reports)
            summary["cases"].append(record)
            summary["named_cases"] += 1
            summary["cpp_assertions"] += record["assertions"]
            summary["decoded_firmware_reports"] += len(reports)
            print("PASS " + name + " (actual setup/loop + actual Jetson parser, host IO only)")
        summary["result"] = "PASS"
        return summary
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        summary["result"] = "FAIL"
        summary["error"] = str(exc)
        raise
    finally:
        with (output / "summary.json").open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_matrix(args.binary, args.output)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, "FIRMWARE_LOOP_FAILED: " + str(exc) + "\n")
    print("Firmware loop: {named_cases} named cases, {cpp_assertions} C++ assertions, "
          "{decoded_firmware_reports} decoded reports PASS; NO physical hardware".format(**result))


if __name__ == "__main__":
    main()
