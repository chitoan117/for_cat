"""Bounded passive recording across manual weight placements.

The only wire command is status. No tare/reference reload/calibration/reset.
Exits if the expected diagnostic RAM calibration changes, the MCU restarts,
serial fails, a stop.request file appears, or the duration limit expires.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM8")
    parser.add_argument("--seconds", type=int, default=1200)
    args = parser.parse_args()
    if not 30 <= args.seconds <= 1800:
        raise ValueError("recording limit: 30..1800 seconds")
    device = next((p for p in list_ports.comports() if p.device.upper() == args.port.upper()), None)
    if device is None or (device.vid, device.pid, device.serial_number) != (0x1A86, 0x55D3, "5C85066678"):
        raise RuntimeError("USB identity mismatch")
    receipt = json.loads((ROOT / "physical/initial_tare_once_receipt.json").read_text(encoding="utf-8"))
    zero = json.loads((Path(receipt["evidence_path"]) / "summary.json").read_text(encoding="utf-8"))
    if not zero.get("zero_window_pass"):
        raise RuntimeError("initial zero window not accepted")
    expected = zero["calibration_after_tare"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT / "physical" / (stamp + "_continuous_reference")
    folder.mkdir(exist_ok=False)
    state = {"pid": os.getpid(), "evidence_path": str(folder), "port": args.port,
             "started_utc": datetime.now(timezone.utc).isoformat(), "duration_limit_s": args.seconds,
             "initial_tare_evidence": receipt["evidence_path"], "expected_calibration": expected,
             "tare_commands_sent": 0, "calibration_commands_sent": 0, "reset_commands_sent": 0,
             "nvs_write_commands_sent": 0, "status_commands_sent": 0, "state": "STARTING",
             "commands": [], "json_messages": 0, "operator_initial_condition": "EMPTY_AFTER_MEASURED_ZERO_WINDOW"}
    (ROOT / "physical/active_recording.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    stream = serial.Serial(port=None, baudrate=115200, timeout=0.1, write_timeout=1)
    stream.dtr = stream.rts = False
    stream.port = args.port
    started = time.monotonic()
    pending = bytearray()
    last_uptime = None
    last_status = -100.0
    confirmed = False
    try:
        with (folder / "serial_raw.bin").open("xb") as raw, (folder / "messages.jsonl").open("x", encoding="utf-8") as messages:
            stream.open()
            while time.monotonic() - started < args.seconds:
                if (folder / "stop.request").exists():
                    state["stop_reason"] = "OPERATOR_STOP_REQUEST"
                    break
                data = stream.read(min(4096, max(1, stream.in_waiting)))
                if data:
                    raw.write(data)
                    raw.flush()
                    pending.extend(data)
                while b"\n" in pending:
                    line, _, rest = pending.partition(b"\n")
                    pending = bytearray(rest)
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        continue  # original bytes retained
                    if not isinstance(message, dict) or message.get("mode") != "HX711_REFERENCE":
                        continue
                    event = {"received_utc": datetime.now(timezone.utc).isoformat(),
                             "elapsed_s": time.monotonic() - started, "message": message}
                    messages.write(json.dumps(event) + "\n")
                    messages.flush()
                    state["json_messages"] += 1
                    uptime = message.get("monotonic_ms")
                    if isinstance(uptime, int):
                        if last_uptime is not None and ((uptime - last_uptime) & 0xFFFFFFFF) > 0x7FFFFFFF:
                            raise RuntimeError("device uptime moved backward; stop without automatic re-tare")
                        last_uptime = uptime
                    if "calibration_source" in message:
                        if not (message.get("calibration_source") == expected["calibration_source"] and
                                isinstance(message.get("offset"), (int, float)) and
                                abs(message["offset"] - expected["offset"]) < 1e-6 and
                                isinstance(message.get("scale_factor_counts_per_gram"), (int, float)) and
                                abs(message["scale_factor_counts_per_gram"] - expected["scale_factor_counts_per_gram"]) < 1e-6 and
                                message.get("servo_locked") is True and message.get("pump_locked") is True and
                                message.get("actuator_outputs_enabled") == 0 and message.get("auto_tare") is False):
                            raise RuntimeError("diagnostic calibration/lock contract changed; no automatic repair")
                        if not confirmed:
                            confirmed = True
                            state["state"] = "RECORDING"
                            state["confirmed_status"] = message
                            (folder / "ready.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
                elapsed = time.monotonic() - started
                if state["json_messages"] and elapsed - last_status >= 5:
                    state["commands"].append({"command": "status", "elapsed_s": elapsed})
                    if stream.write(b"status\n") != len(b"status\n"):
                        raise RuntimeError("short status write")
                    stream.flush()
                    state["status_commands_sent"] += 1
                    last_status = elapsed
                if elapsed > 10 and not confirmed:
                    raise RuntimeError("runtime calibration confirmation timeout")
                if len(pending) > 65536:
                    raise RuntimeError("line buffer limit")
            else:
                state["stop_reason"] = "BOUNDED_DURATION_EXPIRED"
    except Exception as error:
        state["error"] = f"{type(error).__name__}: {error}"
    finally:
        if stream.is_open:
            stream.close()
    state["state"] = "STOPPED_WITH_ERROR" if state.get("error") else "STOPPED"
    state["finished_utc"] = datetime.now(timezone.utc).isoformat()
    state["duration_s"] = time.monotonic() - started
    state["artifacts_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    (folder / "summary.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
