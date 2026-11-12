"""HX711-only preparation: build/config evidence and package; never opens a port."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(r"C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full")
OUT = Path(r"D:\for_cat\HX711_PHYSICAL_BRINGUP_20261021_PREP")
PIO = Path(r"D:\for_cat\.tools-venv\Scripts\pio.exe")
PYTHON = Path(r"D:\for_cat\.venv\Scripts\python.exe")
ZIG = Path(r"D:\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe")
OUT.mkdir(exist_ok=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, args):
    result = subprocess.run(list(map(str, args)), cwd=ROOT, capture_output=True, timeout=300)
    (OUT / name).write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name}: exit {result.returncode}, see full log")
    return result.stdout


status_before = run("git_status_before.txt", ["git", "status", "--short"])
source_names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
source_before = {name: digest(ROOT / name) for name in source_names if name and (ROOT / name).is_file()}
(OUT / "source_hashes_before.json").write_text(json.dumps(source_before, indent=2), encoding="utf-8")
production = ROOT / "jetson/ai/cat_dog_trt.cpp"
assert digest(production) == "9b01288e4b6e450217d3029c2d0b4a3aecafb9dc0e2f87e17289d3e83f5b6366"
run("pio_build_diag_hx711.log", [PIO, "run", "--project-dir", ROOT / "esp32", "-e", "diag_hx711"])
raw = run("resolved_pio_config.json", [PIO, "project", "config", "--project-dir", ROOT / "esp32", "--json-output"])
config = {name: dict(values) for name, values in json.loads(raw)}["env:diag_hx711"]
flags = [flag for line in config["build_flags"] for flag in shlex.split(line)]
for required in ("-DACTUATOR_OUTPUTS_ENABLED=0", "-DSERVO_DIAGNOSTIC_ENABLED=0", "-DPUMP_DIAGNOSTIC_ENABLED=0",
                 "-DM4_DIAGNOSTIC_MODE=1", "-DM4_HX711_INSTALLED=1", "-DM4_SENSOR_BRINGUP=1",
                 "-DFORR_REAL_S3_NO_PSRAM=1", "-DFORR_NATIVE_USB=0", "-DARDUINO_USB_CDC_ON_BOOT=0"):
    assert required in flags, required
assert not any("BOARD_HAS_PSRAM" in f or "SIMULATED_SENSORS" in f for f in flags)
probe = OUT / "compiled_config_probe.cpp"
probe.write_text('''#include <cstdio>
#include "m4/diagnostic_config.h"
#include "m4/actuator_interfaces.h"
static_assert(M4_HX711_DOUT==4 && M4_HX711_SCK==5,"wrong HX711 GPIO");
static_assert(M4_DIAGNOSTIC_MODE==1 && M4_HX711_INSTALLED==1,"wrong isolated mode");
static_assert(M4_SERVO_PWM==-1 && M4_PUMP_MOSFET==-1,"actuator pins assigned");
int main() {
  std::printf("{\\"scope\\":\\"HOST_CONFIG_ONLY\\",\\"dout\\":%d,\\"sck\\":%d,\\"mode\\":%d,\\"actuator_outputs_enabled\\":%d,\\"servo_enabled\\":%d,\\"pump_enabled\\":%d}\\n",
    M4_HX711_DOUT,M4_HX711_SCK,M4_DIAGNOSTIC_MODE,ACTUATOR_OUTPUTS_ENABLED,SERVO_DIAGNOSTIC_ENABLED,PUMP_DIAGNOSTIC_ENABLED);
}
''', encoding="utf-8")
binary = OUT / "compiled_config_probe.exe"
run("compile_config_probe.log", [ZIG, "c++", "-std=c++14", "-Wno-nullability-completeness",
    "-I" + str(ROOT / "esp32/include"), *flags, probe, "-o", binary])
observed = json.loads(run("compiled_config_probe.json", [binary]))
assert observed["dout"] == 4 and observed["sck"] == 5
assert observed["actuator_outputs_enabled"] == observed["servo_enabled"] == observed["pump_enabled"] == 0
run("package.log", [PYTHON, "-B", ROOT / "scripts/prepare_esp32_deploy.py", "--env", "diag_hx711", "--output", OUT / "deploy_hx711"])
manifest = json.loads((OUT / "deploy_hx711/deploy_manifest.json").read_text())
for record in manifest["files"]:
    assert digest(OUT / "deploy_hx711" / record["file"]) == record["sha256"]
esptool = Path(r"C:\Users\chito\.platformio\packages\tool-esptoolpy\esptool.py")
flash_python = Path(r"C:\Users\chito\.platformio\penv\Scripts\python.exe")
run("image_info.log", [flash_python, esptool, "--chip", "esp32s3", "image-info", OUT / "deploy_hx711/firmware.bin"])
run("serial_device_list.txt", [PIO, "device", "list"])
source_after = {name: digest(ROOT / name) for name in source_before}
assert source_before == source_after, "preparation unexpectedly modified source"
summary = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "profile": "diag_hx711", "build": "COMPILE_PASS", "compiled_configuration": observed,
    "board_target": config["board"], "build_flags": flags, "gpio_acquisition": {"DOUT": 4, "SCK": 5},
    "calibration_storage": {"namespace": "m4-calibration", "key": "sensors-v2"},
    "source_unchanged_during_preparation": True, "detector_sha256": digest(production),
    "physical_status": "PHYSICAL_NOT_VERIFIED", "physical_evidence_received": False,
    "serial_ports_opened": 0, "boards_flashed": 0, "servo_enabled": False, "pump_enabled": False,
    "files": manifest["files"], "reference_mass_grams": None, "noise_tolerance": None, "accuracy_tolerance": None,
}
(OUT / "preparation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print("HX711 PREPARED:", OUT)
