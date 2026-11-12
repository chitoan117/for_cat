"""Package only explicit supervised GPIO6 bench firmware. Never opens a board."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "diag_servo_bench"
REQUIRED = (
    "-DACTUATOR_OUTPUTS_ENABLED=0", "-DSERVO_BENCH_MODE=1",
    "-DSERVO_BENCH_PHYSICAL_ENABLE=1", "-DPUMP_DIAGNOSTIC_ENABLED=0",
    "-DSERVO_DIAGNOSTIC_ENABLED=0", "-DFORR_REAL_S3_NO_PSRAM=1",
    "-DFORR_NATIVE_USB=0", "-DARDUINO_USB_CDC_ON_BOOT=0", "-DFORR_HW_SAFE=1",
)


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def prepare(pio, output):
    if output.exists() or not output.parent.is_dir():
        raise ValueError("new output path with existing parent required")
    config = json.loads(subprocess.check_output(
        [str(pio), "project", "config", "--project-dir", str(ROOT / "esp32"), "--json-output"]))
    resolved = dict(dict(config)["env:" + PROFILE])
    flags = [flag for line in resolved["build_flags"] for flag in line.split()]
    if (any(item not in flags for item in REQUIRED) or
            any("SIMULATED_SENSORS" in item or "BOARD_HAS_PSRAM" in item for item in flags)):
        raise ValueError("servo bench is not the isolated no-PSRAM UART0 safety profile")
    build = ROOT / "esp32/.pio/build" / PROFILE
    names = ("bootloader.bin", "partitions.bin", "firmware.bin", "firmware.factory.bin")
    source = {name: build / name for name in names}
    if any(not path.is_file() for path in source.values()):
        raise ValueError("build diag_servo_bench before packaging")
    output.mkdir()
    try:
        records = []
        for name, path in source.items():
            target = output / name
            shutil.copyfile(path, target)
            records.append({"file": name, "bytes": target.stat().st_size, "sha256": sha(target)})
        manifest = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "profile": PROFILE, "board_compile_target": resolved["board"],
            "chip": "ESP32-S3", "expected_flash_mb": 16,
            "physical_status": "NOT_TESTED", "flashed": False,
            "mode": "EXPLICIT_MANUAL_SERVO_GPIO6_BENCH_ONLY",
            "physical_pwm_possible_only_after_manual_config_and_arm": True,
            "pump_enabled": False, "auto_feed_enabled": False,
            "normal_actuator_outputs_enabled": 0,
            "servo_open_close_positions": "UNCONFIGURED_NOT_PHYSICALLY_CALIBRATED",
            "runtime_limits": {"electrical_envelope_us": [1000, 2000],
                               "maximum_initial_configured_span_us": 100,
                               "maximum_arms_per_boot": 3,
                               "arm_timeout_ms": 2000,
                               "move_hold_ms": 250,
                               "close_reference_hold_ms": 350,
                               "hard_deadline_ms": 3000},
            "build_flags": flags, "files": records,
            "flash_warning": "Factory image covers NVS/gaps. Review/backup before supervised flashing. Do not attach servo horn/gate for first pulse test.",
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.pio, args.output), indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, "BENCH_BUNDLE_ABORTED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
