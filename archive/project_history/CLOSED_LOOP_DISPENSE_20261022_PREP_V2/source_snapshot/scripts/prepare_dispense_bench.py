"""Package ONLY an app-only supervised dispense image; never erase HX calibration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = "diag_dispense_bench"
REQUIRED = (
    "-DACTUATOR_OUTPUTS_ENABLED=0", "-DDISPENSE_BENCH_MODE=1",
    "-DDISPENSE_BENCH_PHYSICAL_ENABLE=1", "-DPUMP_DIAGNOSTIC_ENABLED=0",
    "-DSERVO_DIAGNOSTIC_ENABLED=0", "-DFORR_REAL_S3_NO_PSRAM=1",
    "-DFORR_NATIVE_USB=0", "-DARDUINO_USB_CDC_ON_BOOT=0", "-DFORR_HW_SAFE=1",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(pio, prior_hx_bundle, output):
    if output.exists() or not output.parent.is_dir():
        raise ValueError("exclusive output with existing parent required")
    prior_manifest_path = prior_hx_bundle / "deploy_manifest.json"
    hx = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    if hx.get("profile") != "diag_hx711" or hx.get("actuator_outputs_enabled") != 0:
        raise ValueError("matching sensor-only HX711 build manifest required")
    config = json.loads(subprocess.check_output([str(pio), "project", "config",
        "--project-dir", str(ROOT / "esp32"), "--json-output"]))
    resolved = dict(dict(config)["env:" + ENVIRONMENT])
    flags = [flag for line in resolved["build_flags"] for flag in line.split()]
    if any(flag not in flags for flag in REQUIRED) or any(
        "BOARD_HAS_PSRAM" in flag or "SIMULATED_SENSORS" in flag for flag in flags
    ):
        raise ValueError("missing isolated S3 bench protection")
    build = ROOT / "esp32/.pio/build" / ENVIRONMENT
    app = build / "firmware.bin"
    if not app.is_file():
        raise ValueError("build the current dispense bench first")
    matching = {}
    for name in ("bootloader.bin", "partitions.bin"):
        current = build / name
        earlier = prior_hx_bundle / name
        entry = next(item for item in hx["files"] if item["file"] == name)
        if digest(current) != digest(earlier) or digest(earlier) != entry["sha256"]:
            raise ValueError("HX711/dispense bootloader or partitions differ; do not app-only flash")
        matching[name] = digest(current)
    output.mkdir()
    try:
        destination = output / "firmware.bin"
        shutil.copyfile(app, destination)
        manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": ENVIRONMENT, "status": "SUPERVISED_SOFTWARE_ONLY_PHYSICAL_NOT_VERIFIED",
            "chip": "ESP32-S3", "board_compile_target": resolved["board"],
            "application_offset": "0x10000", "flash_mode": "APPLICATION_ONLY_AFTER_VERIFIED_MATCH",
            "factory_image_in_bundle": False, "erases_NVS": False,
            "preexisting_hx_bundle": str(prior_hx_bundle),
            "required_installed_bootloader_sha256": matching["bootloader.bin"],
            "required_installed_partitions_sha256": matching["partitions.bin"],
            "calibration_storage": "m4-calibration/sensors-v2; must be PHYSICALLY verified before use",
            "pump": "OFF_UNTOUCHED", "cat_auto": False, "schedule": False, "web": False,
            "physical_servo_close_confirmed": False, "physical_hx_calibration_confirmed": False,
            "target_grams_configured_by_operator_only": True,
            "bench_serial_requires_manual_inspect_config_arm_and_unique_id": True,
            "normal_ACTUATOR_OUTPUTS_ENABLED": 0,
            "firmware": {"file": destination.name, "bytes": destination.stat().st_size,
                         "sha256": digest(destination)},
            "build_flags": flags,
            "warning": "Do not use the separately built factory image after HX711 calibration: it overwrites NVS. Verify actual device bootloader/partitions against listed SHA before app-only flash.",
        }
        with (output / "deploy_manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2)
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pio", type=Path, required=True)
    parser.add_argument("--hx-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.pio, args.hx_bundle, args.output), indent=2))
    except (OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        parser.exit(2, "DISPENSE_PACKAGE_ABORTED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
