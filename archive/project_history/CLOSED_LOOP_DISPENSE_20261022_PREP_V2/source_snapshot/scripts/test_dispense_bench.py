"""C++14 policy + actual firmware-loop fault matrix with fake HX/LEDC/NVS."""
import argparse
import json
from pathlib import Path
import re
import subprocess

CASES = ("safe_boot", "closed_loop", "reboot", "abort", "nvs_write_fault", "hx_timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--loop", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.policy.is_file() or not args.loop.is_file() or not args.output.parent.is_dir():
        parser.error("binaries and new output parent must exist")
    args.output.mkdir()
    tested = subprocess.run([str(args.policy.resolve())], capture_output=True, text=True, timeout=30)
    (args.output / "portable_policy.log").write_text(tested.stdout + tested.stderr, encoding="utf-8")
    match = re.search(r"DISPENSE_POLICY named=(\d+) assertions=(\d+) PHYSICAL_NOT_TESTED", tested.stdout)
    if tested.returncode or not match or int(match[1]) != 9 or int(match[2]) < 90:
        raise RuntimeError("portable policy did not pass required fault matrix")
    count = 0
    details = []
    for name in CASES:
        serial_log = args.output / (name + ".serial.log")
        command = [str(args.loop.resolve()), name, str(serial_log)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        (args.output / (name + ".execution.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(name + " failed: " + result.stderr)
        record = json.loads(result.stdout)
        if record.get("case") != name or record.get("result") != "PASS" or record.get("physical_hardware") is not False:
            raise RuntimeError("invalid actual-loop result: " + name)
        serial = serial_log.read_text(encoding="utf-8")
        if "GPIO7 PUMP OFF NO CAT/WEB/SCHEDULE" not in serial or "physical_validated=false" not in serial:
            raise RuntimeError("missing isolation status: " + name)
        if name == "closed_loop" and not all(token in serial for token in (
                "event=BASELINE", "event=COARSE", "event=FINE", "event=COMPLETE",
                "baseline_g=0.000", "dispensed_g=3.100", "servo_pwm_attached=0")):
            raise RuntimeError("stable multi-pulse sample transcript incomplete")
        if name == "reboot" and "INSPECTION_REQUIRED" not in serial:
            raise RuntimeError("interrupted session auto resumed after reboot")
        count += record["assertions"]
        details.append(record)
        print("PASS", name, record["assertions"], "host assertions")
    summary = {"scope": "SOFTWARE_ONLY_FAKE_HX_LEDC_NVS", "physical_status": "NOT_TESTED",
               "policy_named_cases": int(match[1]), "policy_assertions": int(match[2]),
               "firmware_loop_named_cases": len(CASES), "firmware_loop_assertions": count,
               "real_firmware_parser_and_setup_loop": True, "real_board_used": False,
               "firmware_loop_cases": details}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DISPENSE HOST PASS:", summary["policy_assertions"], "+", count, "assertions; no physical feed")


if __name__ == "__main__":
    main()
