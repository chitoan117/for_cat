"""Test the actual servo-only firmware loop against fake PWM. No board access."""
import argparse
import json
from pathlib import Path
import subprocess

CASES = ("cold_limits", "expiry_budget", "attach_fault", "write_fault", "hard_deadline",
         "detach_fault", "wrap_and_parser", "reboot_disarms")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.binary.is_file() or not args.output.parent.is_dir():
        parser.error("binary and output parent must exist")
    args.output.mkdir()  # exclusive evidence, never overwrite
    items = []
    for name in CASES:
        log = args.output / (name + ".serial.log")
        execution = subprocess.run([str(args.binary.resolve()), name, str(log)],
                                   capture_output=True, text=True, timeout=30)
        (args.output / (name + ".execution.log")).write_text(execution.stdout + execution.stderr, encoding="utf-8")
        if execution.returncode:
            raise RuntimeError("servo bench host case failed: " + name + " " + execution.stderr)
        row = json.loads(execution.stdout)
        if row.get("case") != name or row.get("result") != "PASS" or row.get("physical_hardware") is not False:
            raise RuntimeError("invalid bench test result: " + name)
        text = log.read_text(encoding="utf-8")
        if "pump_enabled=0 auto_feed_enabled=0" not in text or "GPIO7 PUMP UNTOUCHED" not in text:
            raise RuntimeError("bench report lacks isolated pump/auto status")
        if name == "cold_limits" and not all(part in text for part in (
                "REJECTED_NOT_ARMED", "REJECTED_CONFIG", "action=OPEN result=ACCEPTED",
                "MOVE_TIMEOUT_RETURN_TO_CLOSE_REFERENCE", "PWM_OFF_DISARMED_CLOSE_UNVERIFIED")):
            raise RuntimeError("bench cold/auto-close evidence missing")
        if name == "hard_deadline" and "HARD_DEADLINE_PWM_OFF_CLOSE_UNVERIFIED" not in text:
            raise RuntimeError("bench watchdog deadline not logged")
        if name == "detach_fault" and "PWM_OFF_FAILED_FAULT_REMOVE_SERVO_POWER" not in text:
            raise RuntimeError("failed PWM detach not surfaced")
        items.append(row)
        print("PASS", name, row["assertions"], "host assertions")
    summary = {"scope": "HOST_FAKE_LEDC_REAL_BENCH_LOOP", "named_cases": len(items),
               "assertions": sum(row["assertions"] for row in items), "results": items,
               "physical_validation": "NOT_TESTED", "flashed": False, "pump_gpio_untouched": True}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("SERVO BENCH:", summary["named_cases"], "cases,", summary["assertions"], "assertions; NO physical hardware")


if __name__ == "__main__":
    main()
