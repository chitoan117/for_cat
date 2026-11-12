"""Bounded pre-tare observation; the only device command is 'status'.

Does not flash/reset/tare/calibrate/write NVS. Each run preserves separate raw
evidence, including initial partial lines and all invalid/transient readings.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent


def stats(values: list[float]) -> dict | None:
    if not values:
        return None
    n = max(1, len(values) // 5)
    return {
        "count": len(values), "mean": statistics.fmean(values),
        "min": min(values), "max": max(values), "range": max(values) - min(values),
        "sigma_population": statistics.pstdev(values),
        "first": values[0], "last": values[-1],
        "last_minus_first": values[-1] - values[0],
        "last_fifth_mean_minus_first_fifth_mean": statistics.fmean(values[-n:]) - statistics.fmean(values[:n]),
    }


def numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM8")
    parser.add_argument("--seconds", type=float, default=30)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 60:
        raise ValueError("bounded observation: 5..60 seconds")
    device = next((p for p in list_ports.comports() if p.device.upper() == args.port.upper()), None)
    if device is None or (device.vid, device.pid, device.serial_number) != (0x1A86, 0x55D3, "5C85066678"):
        raise RuntimeError("COM device identity differs from the owner-connected CH343; no serial opened")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = ROOT / "physical" / (stamp + "_empty_pre_tare")
    evidence.mkdir(parents=True, exist_ok=False)
    report = {
        "kind": "HX711_EMPTY_PRE_TARE_OBSERVATION", "started_utc": datetime.now(timezone.utc).isoformat(),
        "operator_condition": "USER_CONFIRMED_EMPTY_IN_CONVERSATION", "port": device.device,
        "usb": {"vid": device.vid, "pid": device.pid, "serial": device.serial_number, "description": device.description},
        "duration_requested_s": args.seconds, "baud": 115200,
        "requested_dtr": False, "requested_rts": False,
        "reset_command_sent": False, "tare_command_sent": False,
        "calibration_command_sent": False, "flash_performed_by_agent": False,
        "commands_sent": [], "physical_calibration_pass": False,
    }
    build = json.loads((ROOT / "result.json").read_text(encoding="utf-8"))
    image = ROOT / "firmware/diag_hx711_reference/firmware.bin"
    report["local_image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    assert report["local_image_sha256"] == build["firmware"]["diag_hx711_reference"]["firmware.bin"]["sha256"]
    report["device_image_identity"] = "USER_FLASH_SCREENSHOT_AND_RUNTIME_MODE_NOT_FLASH_READBACK_HASH"
    events: list[dict] = []
    partial = bytearray()
    sent_status = False
    stream = serial.Serial(port=None, baudrate=115200, timeout=0.1, write_timeout=1)
    stream.dtr = False
    stream.rts = False
    stream.port = args.port
    started = time.monotonic()
    try:
        with (evidence / "serial_raw.bin").open("xb") as raw:
            stream.open()
            started = time.monotonic()
            while time.monotonic() - started < args.seconds:
                received = stream.read(min(4096, max(1, stream.in_waiting)))
                if received:
                    raw.write(received)
                    raw.flush()
                    partial.extend(received)
                while b"\n" in partial:
                    line, _, rest = partial.partition(b"\n")
                    partial = bytearray(rest)
                    text = line.decode("utf-8", "replace").strip()
                    if not text.startswith("{"):
                        continue
                    try:
                        message = json.loads(text)
                    except json.JSONDecodeError:
                        continue  # original bytes remain in serial_raw.bin
                    if message.get("mode") != "HX711_REFERENCE":
                        continue
                    events.append({"received_elapsed_s": time.monotonic() - started, "message": message})
                    if not sent_status:
                        command = b"status\n"
                        if stream.write(command) != len(command):
                            raise RuntimeError("short status write")
                        stream.flush()
                        report["commands_sent"].append({"command": "status", "elapsed_s": time.monotonic() - started})
                        sent_status = True
                if len(partial) > 65536:
                    raise RuntimeError("unbounded line; raw bytes preserved")
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if stream.is_open:
            stream.close()
    report["duration_observed_s"] = time.monotonic() - started
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    raw_path = evidence / "serial_raw.bin"
    raw_bytes = raw_path.read_bytes() if raw_path.exists() else b""
    (evidence / "serial.log").write_text(raw_bytes.decode("utf-8", "replace"), encoding="utf-8", newline="")
    with (evidence / "messages.jsonl").open("x", encoding="utf-8") as output:
        for event in events:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")
    # Full 'status' contains held readings; exclude it from sample statistics.
    compact = [e["message"] for e in events if "calibration_source" not in e["message"]]
    unique: dict[int, dict] = {}
    for message in compact:
        unique.setdefault(message["monotonic_ms"], message)
    samples = list(unique.values())
    full = [e["message"] for e in events if "calibration_source" in e["message"]]
    report["json_messages"] = len(events)
    report["distinct_triplets"] = len(samples)
    report["full_status"] = full
    report["valid_grams_triplets"] = sum(m.get("valid") is True for m in samples)
    report["raw_counts"] = stats([float(m["raw"]) for m in samples if numeric(m.get("raw"))])
    report["median_raw_counts"] = stats([float(m["median_raw"]) for m in samples if numeric(m.get("median_raw"))])
    report["measurement_grams"] = stats([float(m["measurement_grams"]) for m in samples if m.get("valid") is True and numeric(m.get("measurement_grams"))])
    report["display_grams"] = stats([float(m["display_grams"]) for m in samples if m.get("valid") is True and numeric(m.get("display_grams"))])
    report["arduino_reference_projection_only_grams"] = stats([
        (float(m["median_raw"]) - (-668483.0)) / (-1064.4473)
        for m in samples if numeric(m.get("median_raw"))
    ])
    report["projection_note"] = "Offline historical-factor comparison only; NOT device calibrated grams and NOT a PASS. No coefficient was sent to ESP32."
    uptimes = [m["monotonic_ms"] for m in samples]
    report["device_uptime_backward_jumps"] = sum(((b - a) & 0xFFFFFFFF) > 0x7FFFFFFF for a, b in zip(uptimes, uptimes[1:]))
    if len(uptimes) > 1:
        interval_s = ((uptimes[-1] - uptimes[0]) & 0xFFFFFFFF) / 1000
        report["triplet_rate_hz"] = (len(uptimes) - 1) / interval_s if interval_s else None
    columns = ["monotonic_ms", "raw", "median_raw", "measurement_grams", "display_grams", "valid"]
    with (evidence / "triplets.csv").open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(samples)
    report["runtime_observed"] = bool(events)
    report["sensor_data_observed"] = bool(report["median_raw_counts"])
    report["calibration_status"] = full[-1].get("calibration_source") if full else "UNKNOWN"
    if report.get("error"):
        report["outcome"] = "CAPTURE_ERROR"
    elif not samples:
        report["outcome"] = "NO_DISTINCT_TRIPLETS"
    elif report["measurement_grams"] is None:
        report["outcome"] = "RAW_ONLY_NO_VALID_CALIBRATED_GRAMS"
    else:
        report["outcome"] = "PRE_TARE_GRAMS_OBSERVED_NOT_PHYSICAL_PASS"
    report["artifacts_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence.iterdir() if p.is_file()
    }
    (evidence / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence_path": str(evidence), **report}, indent=2))


if __name__ == "__main__":
    main()
