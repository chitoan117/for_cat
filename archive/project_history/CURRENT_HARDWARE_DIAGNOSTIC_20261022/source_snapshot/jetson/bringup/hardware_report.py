"""Physical report TEMPLATE/operator records; never discovers, flashes or passes hardware."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

TESTS = ("board_identity_flash_memory", "serial_link", "safe_gpio", "oled", "rtc",
         "pir", "approach_distance", "food_reservoir", "water_operational", "water_reservoir",
         "hx711_load_cell", "servo_closed_loop", "pump_f5305s", "actuators_still_disabled")
STATES = ("PASS", "FAIL", "SKIPPED", "NOT_INSTALLED", "NOT_TESTED")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(65536), b""):
            value.update(data)
    return value.hexdigest()


def validate(data):
    if data.get("schema_version") != 2 or data.get("report_scope") != "PHYSICAL_VALIDATION_RECORD":
        raise ValueError("wrong physical report schema/scope")
    if data.get("physical_validation_automatically_awarded") is not False:
        raise ValueError("physical PASS cannot be automatically awarded")
    if set(data.get("tests", {})) != set(TESTS):
        raise ValueError("wrong physical test matrix")
    not_wired = data.get("not_wired_tests", [])
    if not isinstance(not_wired, list) or not set(not_wired) <= set(TESTS):
        raise ValueError("invalid not-wired status declaration")
    for name, row in data["tests"].items():
        if row.get("status") not in STATES or not isinstance(row.get("evidence"), list):
            raise ValueError("invalid physical test result")
        if row["status"] in ("PASS", "FAIL") and (not row.get("operator") or not row.get("tested_at") or not row["evidence"]):
            raise ValueError("actual result needs operator/time/evidence")
        if name == "hx711_load_cell" and data["hx711_installed"] is not True and row["status"] == "PASS":
            raise ValueError("uninstalled load cell cannot PASS")
        if name in not_wired and row["status"] == "PASS":
            raise ValueError("not-wired sensor cannot PASS")
    return data


def template(config_path, manifest_path, identity="NOT_IDENTIFIED"):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if config.get("actuator_outputs_enabled") != 0 or config.get("servo_enabled") is not False or config.get("pump_enabled") is not False:
        raise ValueError("bring-up config must keep actuators disabled")
    firmware = next(item for item in manifest["files"] if item["file"] == "firmware.bin")
    installed = config["hx711"]["installed"]
    if installed is not None and type(installed) is not bool:
        raise ValueError("installation is true/false/null (unconfirmed)")
    not_wired = set(config.get("owner_reported_not_wired", []))
    absent = {"food_reservoir"} if "hc_sr04_2" in not_wired else set()
    if "jsn_sr04t_2" in not_wired:
        absent.add("water_reservoir")
    if installed is False:
        absent.add("hx711_load_cell")
    data = {"schema_version": 2, "report_scope": "PHYSICAL_VALIDATION_RECORD",
            "created_at": datetime.now(timezone.utc).isoformat(), "board_identity": identity,
            "firmware_sha256": firmware["sha256"], "configuration_sha256": digest(config_path),
            "hx711_installed": installed, "not_wired_tests": sorted(absent - {"hx711_load_cell"}),
            "physical_validation_automatically_awarded": False,
            "tests": {name: {"status": "NOT_INSTALLED" if name in absent else "NOT_TESTED",
                             "tested_at": None, "operator": None, "evidence": []} for name in TESTS}}
    return validate(data)


def record(data, name, status, operator, evidence):
    validate(data)
    if name not in TESTS or status not in STATES:
        raise ValueError("unknown test/status")
    entries = []
    for path in evidence:
        path = Path(path).resolve()
        entries.append({"path": str(path), "sha256": digest(path), "source": "OPERATOR_SUPPLIED_PHYSICAL_EVIDENCE"})
    data["tests"][name] = {"status": status, "tested_at": datetime.now(timezone.utc).isoformat(),
                           "operator": operator, "evidence": entries}
    return validate(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--identity", default="NOT_IDENTIFIED")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--test", choices=TESTS)
    parser.add_argument("--status", choices=STATES)
    parser.add_argument("--operator")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input:
            if not args.test or not args.status:
                raise ValueError("recording requires test/status")
            data = record(json.loads(args.input.read_text()), args.test, args.status, args.operator, args.evidence)
        else:
            if not args.config or not args.manifest:
                raise ValueError("template requires config and firmware manifest")
            data = template(args.config, args.manifest, args.identity)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        parser.exit(2, "PHYSICAL_REPORT_ERROR: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
