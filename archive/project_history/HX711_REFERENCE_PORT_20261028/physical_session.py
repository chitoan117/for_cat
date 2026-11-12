"""Bounded, evidence-preserving HX711 reference observations on the known CH343.

initial-empty: explicit reference RAM, 30s pre-tare, at most ONE guarded initial
tare per explicitly confirmed boot session, then 30s zero. A new receipt requires
raw baseline evidence of restart and live same-boot verification; old receipts
are retained. weight: read/status only, never tare/refit.
Does not flash, reset, write NVS or send actuator commands.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import serial
from serial.tools import list_ports

from capture_empty import numeric, stats

ROOT = Path(__file__).resolve().parent
PHYSICAL = ROOT / "physical"
TARE_RECEIPT = PHYSICAL / "initial_tare_once_receipt.json"


class Observation:
    def __init__(self, port: str, folder: Path):
        self.folder = folder
        self.raw = (folder / "serial_raw.bin").open("xb")
        self.messages = (folder / "messages.jsonl").open("x", encoding="utf-8")
        self.rows: list[dict] = []
        self.commands: list[dict] = []
        self.lines: list[dict] = []
        self.partial = bytearray()
        self.phase = "INITIAL_STATUS"
        self.started = time.monotonic()
        self.serial = serial.Serial(port=None, baudrate=115200, timeout=0.1, write_timeout=1)
        self.serial.dtr = self.serial.rts = False
        self.serial.port = port

    def open(self):
        self.serial.open()

    def read(self, seconds: float):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            data = self.serial.read(min(4096, max(1, self.serial.in_waiting)))
            if data:
                self.raw.write(data)
                self.raw.flush()
                self.partial.extend(data)
            while b"\n" in self.partial:
                line, _, rest = self.partial.partition(b"\n")
                self.partial = bytearray(rest)
                text = line.decode("utf-8", "replace").strip()
                event = {"phase": self.phase, "elapsed_s": time.monotonic() - self.started, "line": text}
                self.lines.append(event)
                if text.startswith("{"):
                    try:
                        message = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if message.get("mode") == "HX711_REFERENCE":
                        row = {"phase": self.phase, "elapsed_s": event["elapsed_s"], "message": message}
                        self.rows.append(row)
                        self.messages.write(json.dumps(row) + "\n")
                        self.messages.flush()
            if len(self.partial) > 65536:
                raise RuntimeError("line exceeds bounded buffer; raw preserved")

    def send(self, command: str):
        if command not in {"status", "reference CONFIRM", "t"}:
            raise ValueError("command not whitelisted")
        self.commands.append({"phase": self.phase, "elapsed_s": time.monotonic() - self.started, "command": command})
        # Intent is saved BEFORE any write; a failed/partial tare is not retried.
        (self.folder / "commands.json").write_text(json.dumps(self.commands, indent=2), encoding="utf-8")
        wire = (command + "\n").encode("ascii")
        if self.serial.write(wire) != len(wire):
            raise RuntimeError("short command write; do not retry")
        self.serial.flush()

    def status(self) -> dict:
        count = len(self.rows)
        self.send("status")
        self.read(1)
        full = [r["message"] for r in self.rows[count:] if "calibration_source" in r["message"]]
        if not full:
            raise RuntimeError("no fresh full status response")
        result = full[-1]
        if not (result.get("servo_locked") is True and result.get("pump_locked") is True and
                result.get("actuator_outputs_enabled") == 0 and result.get("auto_tare") is False and
                result.get("nvs_key") == "sensors-v2"):
            raise RuntimeError("runtime diagnostic contract differs")
        return result

    def samples(self, phase: str) -> list[dict]:
        unique = {}
        for row in self.rows:
            m = row["message"]
            if row["phase"] == phase and "calibration_source" not in m:
                unique.setdefault(m["monotonic_ms"], m)
        return list(unique.values())

    def summary(self, phase: str) -> dict:
        samples = self.samples(phase)
        valid = [m for m in samples if m.get("valid") is True and numeric(m.get("measurement_grams"))]
        return {
            "phase": phase, "triplets": len(samples), "valid_grams_triplets": len(valid),
            "measurement_grams": stats([m["measurement_grams"] for m in valid]),
            "display_grams": stats([m["display_grams"] for m in valid if numeric(m.get("display_grams"))]),
            "median_raw_counts": stats([m["median_raw"] for m in samples if numeric(m.get("median_raw"))]),
        }

    def close(self):
        if self.serial.is_open:
            self.serial.close()
        self.raw.close()
        self.messages.close()


def stable(window: dict) -> bool:
    value = window["measurement_grams"]
    return bool(value and window["valid_grams_triplets"] >= 60 and
                window["valid_grams_triplets"] == window["triplets"] and
                value["range"] <= 0.20 and value["sigma_population"] <= 0.05 and
                abs(value["last_fifth_mean_minus_first_fifth_mean"]) <= 0.10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("initial-empty", "weight"))
    parser.add_argument("--port", default="COM8")
    parser.add_argument("--mass", type=float)
    parser.add_argument("--tare-once", action="store_true")
    parser.add_argument("--session-receipt", type=Path, default=TARE_RECEIPT)
    parser.add_argument("--restart-baseline", type=Path)
    args = parser.parse_args()
    receipt_path = args.session_receipt.resolve()
    if receipt_path.parent != PHYSICAL.resolve():
        raise RuntimeError("session receipt must be a direct child of the physical evidence directory")
    if args.mode == "initial-empty" and (not args.tare_once or receipt_path.exists()):
        raise RuntimeError("explicit --tare-once required; existing initial tare receipt forbids automatic repeat")
    restart_baseline = None
    if args.mode == "initial-empty" and receipt_path != TARE_RECEIPT.resolve():
        if args.restart_baseline is None:
            raise RuntimeError("new initial-tare receipt requires explicit restart baseline evidence")
        restart_baseline = json.loads(args.restart_baseline.read_text(encoding="utf-8"))
        original_receipt = json.loads(TARE_RECEIPT.read_text(encoding="utf-8"))
        original_session = json.loads((Path(original_receipt["evidence_path"]) / "summary.json").read_text(encoding="utf-8"))
        baseline_status = restart_baseline["full_status"][0]
        gap_s = (datetime.fromisoformat(restart_baseline["started_utc"]) - datetime.fromisoformat(original_session["finished_utc"])).total_seconds()
        if not (restart_baseline["kind"] == "HX711_EMPTY_PRE_TARE_OBSERVATION" and
                restart_baseline["calibration_status"] == "NONE" and
                restart_baseline["distinct_triplets"] >= 60 and
                baseline_status["calibration_source"] == "NONE" and
                baseline_status["monotonic_ms"] < original_session["final_status"]["monotonic_ms"] and
                0 < gap_s < 4294967):
            raise RuntimeError("baseline does not establish a restarted, raw-observed empty session")
    if args.mode == "weight" and (args.tare_once or args.mass not in {0, 5, 10, 20, 35, 38}):
        raise RuntimeError("weight observation requires a listed mass and never permits tare")
    device = next((p for p in list_ports.comports() if p.device.upper() == args.port.upper()), None)
    if device is None or (device.vid, device.pid, device.serial_number) != (0x1A86, 0x55D3, "5C85066678"):
        raise RuntimeError("USB device identity mismatch; no port opened")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = "initial_reference_zero" if args.mode == "initial-empty" else f"observe_{args.mass:g}g"
    folder = PHYSICAL / (stamp + "_" + suffix)
    folder.mkdir(parents=True, exist_ok=False)
    report = {"kind": "HX711_REFERENCE_PHYSICAL_OBSERVATION", "mode": args.mode,
              "started_utc": datetime.now(timezone.utc).isoformat(), "port": args.port,
              "operator_mass_g": 0 if args.mode == "initial-empty" else args.mass,
              "operator_mass_source": "USER_PLACEMENT_DECLARATION_NOT_AUTOMATIC_RECOGNITION",
              "session_receipt_path": str(receipt_path),
              "calibration_authority": "DIAGNOSTIC_RAM_ONLY_NOT_PRODUCTION_ACTIVATION",
              "nvs_write_command_sent": False, "reset_command_sent": False,
              "flash_performed_by_agent": False, "refit": False, "physical_full_calibration_pass": False}
    observation = Observation(args.port, folder)
    try:
        observation.open()
        observation.read(1)
        if not observation.rows:
            raise RuntimeError("golden diagnostic mode not observed")
        report["initial_status"] = observation.status()
        if args.mode == "initial-empty":
            if report["initial_status"]["calibration_source"] != "NONE":
                raise RuntimeError("calibration source unexpectedly changed since pre-tare baseline; stop")
            if restart_baseline is not None:
                baseline_status = restart_baseline["full_status"][0]
                host_elapsed_s = (datetime.now(timezone.utc) - datetime.fromisoformat(restart_baseline["started_utc"])).total_seconds()
                device_elapsed_s = ((report["initial_status"]["monotonic_ms"] - baseline_status["monotonic_ms"]) & 0xFFFFFFFF) / 1000
                if abs(host_elapsed_s - device_elapsed_s) > 3:
                    raise RuntimeError("live boot no longer matches restart raw baseline; do not tare")
                report["restart_context"] = {
                    "baseline_path": str(args.restart_baseline.resolve()),
                    "host_elapsed_s": host_elapsed_s, "device_elapsed_s": device_elapsed_s,
                    "same_boot_verified": True, "original_receipt_retained": str(TARE_RECEIPT),
                    "operator_setup_statement": "Owner reports scale/fixture unchanged; current empty confirmed",
                    "scope": "New post-restart RAM diagnostic session; inter-session zero shift remains recorded and unresolved",
                }
            observation.phase = "SELECT_REFERENCE"
            observation.send("reference CONFIRM")
            selected = observation.status()
            if not (selected["calibration_source"] == "ARDUINO_REFERENCE_RAM_ONLY" and selected["offset"] == -668483 and
                    abs(selected["scale_factor_counts_per_gram"] - (-1064.4473)) < 1e-6):
                raise RuntimeError("reference selection not confirmed")
            report["reference_status"] = selected
            observation.phase = "REFERENCE_PRE_TARE"
            observation.read(30)
            report["pre_tare"] = observation.summary("REFERENCE_PRE_TARE")
            if not stable(report["pre_tare"]):
                raise RuntimeError("pre-tare data unstable/incomplete; NO TARE to conceal instability")
            observation.phase = "TARE_ONCE"
            receipt = {"intent_utc": datetime.now(timezone.utc).isoformat(), "evidence_path": str(folder),
                       "command": "t", "scope": "ONE_EXPLICIT_INITIAL_EMPTY_TARE_RAM_ONLY", "command_result": "INTENT_RECORDED_NO_RETRY"}
            receipt["restart_context"] = report.get("restart_context")
            with receipt_path.open("x", encoding="utf-8") as output:
                json.dump(receipt, output, indent=2)
            observation.send("t")
            observation.read(5)
            acknowledgments = [line["line"] for line in observation.lines if line["phase"] == "TARE_ONCE" and line["line"].startswith("TARE_OK OFFSET=")]
            if len(acknowledgments) != 1:
                raise RuntimeError("single TARE_OK not confirmed; stop without retry")
            after = observation.status()
            if not (after["calibration_source"] == "EXPLICIT_TARE_RAM_ONLY" and after["tare_pending"] is False and
                    abs(after["scale_factor_counts_per_gram"] - selected["scale_factor_counts_per_gram"]) < 1e-6):
                raise RuntimeError("tare slope/source changed unexpectedly")
            report["tare_ack"] = acknowledgments[0]
            report["calibration_after_tare"] = after
            observation.phase = "EMPTY_POST_TARE"
            observation.read(30)
            report["post_tare"] = observation.summary("EMPTY_POST_TARE")
            report["zero_window_pass"] = bool(stable(report["post_tare"]) and abs(report["post_tare"]["measurement_grams"]["mean"]) <= 0.10)
        else:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            previous = json.loads((Path(receipt["evidence_path"]) / "summary.json").read_text(encoding="utf-8"))
            expected = previous["calibration_after_tare"]
            current = report["initial_status"]
            if not (current["calibration_source"] == expected["calibration_source"] and
                    abs(current["offset"] - expected["offset"]) < 1e-6 and
                    abs(current["scale_factor_counts_per_gram"] - expected["scale_factor_counts_per_gram"]) < 1e-6):
                raise RuntimeError("RAM calibration no longer matches initial tare; do not re-tare/reload automatically")
            report["initial_tare_evidence"] = receipt["evidence_path"]
            observation.phase = "SETTLE_KEEP_TRANSIENTS"
            observation.read(3)
            observation.phase = "WEIGHT_WINDOW"
            observation.read(30)
            report["weight_window"] = observation.summary("WEIGHT_WINDOW")
            mean = report["weight_window"]["measurement_grams"]
            # Owner explicitly accepts 0.3..0.7g error for this demo. Keep
            # measured values unchanged; update the test threshold, not the fit.
            report["acceptance_profile"] = "OWNER_DEMO_20261028_NONZERO_PLUS_MINUS_0_7G"
            report["tolerance_g"] = 0.10 if args.mass == 0 else 0.70
            report["signed_error_g"] = mean["mean"] - args.mass if mean else None
            report["weight_window_pass"] = bool(stable(report["weight_window"]) and mean and abs(mean["mean"] - args.mass) <= report["tolerance_g"])
        report["final_status"] = observation.status()
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        observation.close()
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["commands_sent"] = observation.commands
    report["tare_commands_sent"] = sum(c["command"] == "t" for c in observation.commands)
    report["outcome"] = "STOPPED_WITH_ERROR_NO_RETRY" if report.get("error") else "WINDOWS_RECORDED_NOT_FULL_CALIBRATION_PASS"
    raw = (folder / "serial_raw.bin").read_bytes()
    (folder / "serial.log").write_text(raw.decode("utf-8", "replace"), encoding="utf-8", newline="")
    with (folder / "triplets.csv").open("x", encoding="utf-8", newline="") as output:
        fields = ["phase", "monotonic_ms", "raw", "median_raw", "measurement_grams", "display_grams", "valid"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for phase in dict.fromkeys(r["phase"] for r in observation.rows):
            writer.writerows({"phase": phase, **m} for m in observation.samples(phase))
    report["artifacts_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
    (folder / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence_path": str(folder), **report}, indent=2))


if __name__ == "__main__":
    main()
