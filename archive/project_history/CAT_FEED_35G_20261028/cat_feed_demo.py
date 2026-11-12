"""One supervised CAT-only food episode; no inference/camera ownership here.

Read the existing C++ detector's canonical ai_latest table. DOG never initiates
motion. A fresh NONE interval then fresh stable CAT enables one35g request.
The ESP32 owns the mass stop and lease-expiry close even if this process dies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
import time


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def read_ai(path, now, boot_id):
    unknown = {"classification": "UNKNOWN", "health": "STALE", "updated_monotonic_ms": None}
    try:
        with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2) as db:
            row = db.execute("SELECT body FROM ai_latest WHERE id=1").fetchone()
        if not row or not isinstance(row[0], str) or len(row[0]) > 4096:
            return unknown
        data = json.loads(row[0])
        stamp = data.get("updated_monotonic_ms")
        if not (data.get("host_boot_id") == boot_id and data.get("actuator_execution") is False and
                data.get("health") == "ONLINE" and finite(stamp) and 0 <= now - stamp / 1000 <= 1.5):
            return unknown
        species = data.get("classification")
        confidence = data.get("confidence")
        if species in {"CAT", "DOG"} and finite(confidence) and 0 <= confidence <= 1:
            return data
        if species == "NONE" and confidence is None:
            return data
        return unknown
    except (OSError, sqlite3.Error, ValueError, TypeError, AttributeError):
        return unknown


class CatGate:
    def __init__(self):
        self.none_since = self.cat_since = None
        self.clear_seen = False
        self.fired = False
        self.stop_sent = False
        self.cat_stamps = set()

    def update(self, ai, device, now):
        species = ai.get("classification") if ai.get("health") == "ONLINE" else "UNKNOWN"
        confidence = ai.get("confidence")
        cat = species == "CAT" and finite(confidence) and confidence >= 0.35
        if self.fired:
            if device.get("state") in {"BASELINE", "OPEN"}:
                if cat:
                    return "cat"
                if not self.stop_sent:
                    self.stop_sent = True
                    return "stop"
            return None
        if species == "NONE":
            if self.none_since is None:
                self.none_since = now
            if now - self.none_since >= 1.0:
                self.clear_seen = True
            self.cat_since = None
            self.cat_stamps.clear()
            return None
        self.none_since = None
        if not cat:
            self.cat_since = None
            self.cat_stamps.clear()
            if species in {"DOG", "UNKNOWN"}:
                self.clear_seen = False
            return None
        if not self.clear_seen:
            return None
        if self.cat_since is None:
            self.cat_since = now
        stamp = ai.get("updated_monotonic_ms")
        if finite(stamp):
            self.cat_stamps.add(stamp)
        # Bound memory while waiting; at least two genuinely distinct AI reports.
        if len(self.cat_stamps) > 16:
            self.cat_stamps = set(sorted(self.cat_stamps)[-16:])
        ready = (device.get("mode") == "CAT_FEED_35G" and device.get("state") == "IDLE" and
                 device.get("journal_ready") is True and device.get("pending") is False and
                 device.get("calibrated") is True and finite(device.get("measurement_grams")) and
                 device.get("pump_locked") is True)
        if ready and now - self.cat_since >= 0.8 and len(self.cat_stamps) >= 2:
            self.fired = True
            return "feed"
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--db", default="/home/toan/for_cat/jetson/data/events.db")
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--calibration-file")
    parser.add_argument("--duration", type=float, default=180)
    args = parser.parse_args()
    if args.execute or args.provision:
        parser.error("SUPERSEDED: owner requires HX711 PHYSICAL_VALIDATION_PENDING, servo/pump LOCKED; use CAT_APPROACH_DOG_BUZZER_20261028")
    if not 5 <= args.duration <= 600 or args.execute and args.provision:
        parser.error("bounded5..600s; provision and execute are separate operations")
    import serial
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=False)
    transcript = (folder / "events.jsonl").open("x", encoding="utf-8")
    raw = (folder / "serial_raw.bin").open("xb")
    started = time.monotonic()
    result = {"started_utc": datetime.now(timezone.utc).isoformat(), "feed_request_sent": False,
              "actuator_execution_reported": False, "commands": []}

    def log(kind, **data):
        event = {"kind": kind, "elapsed_s": time.monotonic() - started, **data}
        transcript.write(json.dumps(event) + "\n")
        transcript.flush()

    port = serial.Serial(port=None, baudrate=115200, timeout=0.05, write_timeout=0.5, exclusive=True)
    port.dtr = port.rts = False
    port.port = args.port
    pending = bytearray()
    latest = {}
    latest_at = -100.0
    lines = []

    def pump(seconds):
        nonlocal pending, latest, latest_at
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            data = port.read(min(4096, max(1, port.in_waiting)))
            if data:
                raw.write(data)
                raw.flush()
                pending.extend(data)
            while b"\n" in pending:
                line, _, rest = pending.partition(b"\n")
                pending = bytearray(rest)
                text = line.decode("utf-8", "replace").strip()
                log("rx", line=text)
                lines.append(text)
                del lines[:-100]
                try:
                    data = json.loads(text)
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("mode") == "CAT_FEED_35G":
                    latest = data
                    latest_at = time.monotonic()
            if len(pending) > 16384:
                raise RuntimeError("UART line exceeds bound / wrong firmware")

    def send(text):
        result["commands"].append({"elapsed_s": time.monotonic() - started, "command": text})
        log("tx", command=text)
        wire = (text + "\n").encode("ascii")
        if port.write(wire) != len(wire):
            raise RuntimeError("short command write; no automatic retry")
        port.flush()

    gate = CatGate()
    request_id = None
    try:
        port.open()
        send("status")
        pump(2)
        if not latest:
            raise RuntimeError("CAT_FEED_35G firmware not observed; flash the new application first")
        if latest.get("close_degrees") != 90 or latest.get("open_degrees") != 45 or latest.get("pump_locked") is not True:
            raise RuntimeError("firmware position/pump contract differs")
        result["initial_status"] = dict(latest)
        if args.provision:
            if latest.get("pending") is not False or latest.get("state") != "IDLE":
                raise RuntimeError("pending/corrupt or busy journal: no automatic recovery")
            if not latest.get("calibrated"):
                if not args.calibration_file:
                    raise RuntimeError("missing calibration: explicit validated input required")
                cal = json.loads(Path(args.calibration_file).read_text(encoding="utf-8"))
                offset, factor = cal["offset_counts"], cal["counts_per_gram"]
                if not finite(offset) or not finite(factor) or factor == 0:
                    raise RuntimeError("invalid calibration input")
                send("calset {:.12f} {:.12f} SAVE".format(offset, factor))
                pump(2)
                if "CALIBRATION_SAVED_READBACK_OK NO_TARE NO_REFIT" not in lines:
                    raise RuntimeError("calibration save/readback not confirmed")
                result["calibration_input"] = cal
            if not latest.get("journal_ready"):
                send("journal init CONFIRM")
                pump(1)
                if "JOURNAL_INITIALIZED" not in lines:
                    raise RuntimeError("journal initialization not confirmed")
            send("status")
            pump(1)
            if not (latest.get("calibrated") is True and latest.get("journal_ready") is True and latest.get("pending") is False):
                raise RuntimeError("provisioned state incomplete")
            result["outcome"] = "PROVISIONED_NO_MOVEMENT"
        elif not args.execute:
            result["outcome"] = "STATUS_ONLY_NO_MOVEMENT"
        else:
            if not (latest.get("state") == "IDLE" and latest.get("calibrated") is True and
                    latest.get("journal_ready") is True and latest.get("pending") is False):
                raise RuntimeError("device not provisioned/idle; execute never repairs calibration/journal")
            request_id = latest["last_id"] + 1
            if type(request_id) is not int or not 1 <= request_id < 0xFFFFFFFF:
                raise RuntimeError("request ID budget exhausted")
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            stop_at = time.monotonic() + args.duration
            next_lease = 0.0
            log("waiting_for_none_then_cat", request_id=request_id, target_grams=35)
            while time.monotonic() < stop_at:
                pump(0.1)
                now = time.monotonic()
                if now - latest_at > 1:
                    raise RuntimeError("device telemetry stale")
                ai = read_ai(args.db, now, boot_id)
                action = gate.update(ai, latest, now)
                log("ai_gate", classification=ai.get("classification"), health=ai.get("health"), action=action)
                if action == "feed":
                    send("feed " + str(request_id))
                    result["feed_request_sent"] = True
                    next_lease = now
                elif action == "stop":
                    send("stop")
                if gate.fired and action in {"cat", "feed"} and now >= next_lease:
                    send("cat " + str(request_id))
                    next_lease = now + 0.15
                if latest.get("state") == "FAULT":
                    raise RuntimeError("ESP32 latched fault: " + str(latest.get("reason")))
                if latest.get("state") == "OPEN" and latest.get("pwm_attached") is True:
                    result["actuator_execution_reported"] = True
                if gate.fired and latest.get("state") == "COMPLETE" and latest.get("id") == request_id:
                    result["outcome"] = "ONE_EPISODE_COMPLETE_SENSOR_REPORTED_NOT_PHYSICAL_CERTIFICATE"
                    break
            else:
                result["outcome"] = "NO_CAT_EPISODE" if not gate.fired else "HOST_DURATION_EXPIRED"
    except Exception as error:
        result["error"] = "{}: {}".format(type(error).__name__, error)
        result["outcome"] = "STOPPED_WITH_ERROR_NO_RETRY"
    finally:
        if port.is_open:
            if latest.get("state") in {"BASELINE", "OPEN"}:
                try:
                    send("stop")
                    pump(1)
                except Exception as error:
                    result["close_error"] = str(error)
            port.close()
        result["final_status"] = latest
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (folder / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        transcript.close()
        raw.close()
    print(json.dumps(result, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
