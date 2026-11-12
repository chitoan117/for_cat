"""Offline HX711-only checks/build/package. Never opens serial or contacts a host."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
FW = ROOT / "FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32"
ORIGINAL = Path(r"C:\Users\chito\OneDrive\Desktop\CODE_TEST_LOADCELL_CHUAN")
ZIG = ROOT / ".tools-zig/zig-x86_64-windows-0.16.0/zig.exe"
PIO_PYTHON = Path(r"C:\Users\chito\.platformio\penv\Scripts\python.exe")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], log: str, timeout: int = 360) -> str:
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    (OUT / log).write_bytes(result.stdout)
    text = result.stdout.decode("utf-8", "replace")
    if result.returncode:
        print(text)
        raise RuntimeError(f"exit={result.returncode}; see {OUT / log}")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    assert OUT.is_dir() and FW.is_dir() and ORIGINAL.is_dir()
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "kind": "ESP32_HX711_REFERENCE_PORT", "physical_result": "NOT_TESTED",
              "flash_performed": False, "serial_opened": False, "network_used": False,
              "actuator_outputs_enabled": 0, "auto_tare": False, "refit": False}
    source = ORIGINAL / "CODE_TEST_LOADCELL_CHUAN.ino"
    archive = OUT / "reference/CODE_TEST_LOADCELL_CHUAN.ino"
    assert source.read_text(encoding="utf-8-sig").rstrip("\n") == archive.read_text(encoding="utf-8-sig").rstrip("\n"), "reference text mismatch"
    log = ORIGINAL / "data_test.txt"
    # Raw user evidence is an input artifact: preserve every byte, no editing.
    saved_log = OUT / "reference/data_test.txt"
    if saved_log.exists():
        assert saved_log.read_bytes() == log.read_bytes(), "do not overwrite old evidence"
    else:
        shutil.copyfile(log, saved_log)
    result["reference"] = {
        "marker": "PHYSICAL_VALIDATED_ARDUINO_HX711_REFERENCE",
        "original_path": str(source), "original_sha256": sha(source),
        "archive_sha256": sha(archive), "normalized_text_equal": True,
        "normalization": "UTF-8 BOM/newlines/final newline only; code and whitespace otherwise unchanged",
        "serial_original_path": str(log), "serial_sha256": sha(log),
        "serial_archive_sha256": sha(saved_log),
        "authority": "OWNER_PHYSICAL_ARDUINO_ONLY_NOT_ESP32_PASS"}

    # Limit the scope check to the firmware source manifest already captured at
    # the prior guard milestone; no repository-wide audit or cleanup.
    baseline_path = FW.parent / "release_manifest.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["source_sha256"]
    changed = [name for name, digest in baseline.items() if sha(FW / name) != digest]
    assert set(changed) == {"platformio.ini", "include/m4/hx711.h", "test/native_drivers.cpp"}, changed
    result["existing_firmware_files_changed"] = sorted(changed)
    result["baseline_manifest_sha256"] = sha(baseline_path)
    result["unchanged_baseline_source_files"] = len(baseline) - len(changed)

    (OUT / "native").mkdir(exist_ok=True)
    tests = [
        ("hx711_reference", [], "HX711_REFERENCE_SOFTWARE_PASS"),
        ("hx711_reference_loop", [], "HX711_REFERENCE_LOOP_SOFTWARE_PASS"),
        ("native_drivers", ["--hx711-only"], "HX711 legacy regression:"),
    ]
    result["focused_tests"] = []
    for name, arguments, marker in tests:
        exe = OUT / "native" / (name + ".exe")
        command = [str(ZIG), "c++", "-std=c++17", "-O1", "-Wall", "-Wextra",
                   "-I" + str(FW / "test/arduino_stub"), "-I" + str(FW / "include"),
                   str(FW / "test" / (name + ".cpp")), "-o", str(exe)]
        run(command, name + "_compile.log")
        output = run([str(exe), *arguments], name + "_test.log")
        assert marker in output
        match = re.search(r"(?:assertions=|regression: )(\d+)", output)
        result["focused_tests"].append({"name": name, "status": "PASS",
                                         "assertions": int(match.group(1)) if match else None})
        # Validate actual diagnostic JSON, including null/error, not a string fixture.
        if name == "hx711_reference_loop":
            messages = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
            assert messages and all(m["servo_locked"] and m["pump_locked"] for m in messages)
            assert messages[-1]["display_grams"] is None and not messages[-1]["valid"]
        print(output.splitlines()[-1])

    if args.build:
        run([str(PIO_PYTHON), "-m", "platformio", "run", "--project-dir", str(FW),
             "-e", "diag_hx711_reference", "-e", "diag_four_ultrasonic"], "build.log", 600)
        result["build"] = {"diag_hx711_reference": "PASS", "diag_four_ultrasonic": "PASS"}
        release = OUT / "firmware"
        release.mkdir(exist_ok=True)
        result["firmware"] = {}
        for profile in result["build"]:
            target = release / profile
            target.mkdir(exist_ok=True)
            result["firmware"][profile] = {}
            for name in ("firmware.bin", "firmware.elf", "bootloader.bin", "partitions.bin"):
                artifact = FW / ".pio/build" / profile / name
                shutil.copyfile(artifact, target / name)
                result["firmware"][profile][name] = {"sha256": sha(target / name), "bytes": artifact.stat().st_size}
        result["primary_manual_flash_image"] = str(release / "diag_hx711_reference/firmware.bin")
        result["application_offset"] = "0x10000"
        result["erase_flash_or_nvs"] = False
    result["source_sha256"] = {
        p.relative_to(FW).as_posix(): sha(p)
        for base in (FW / "include", FW / "src", FW / "test")
        for p in base.rglob("*") if p.is_file()
    }
    result["source_sha256"]["platformio.ini"] = sha(FW / "platformio.ini")
    result["ESP32_HX711_REFERENCE_PORT_READY"] = bool(args.build)
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"focused_suites": len(tests), "build": result.get("build", "NOT_RUN"),
                      "physical_result": "NOT_TESTED", "ready": result["ESP32_HX711_REFERENCE_PORT_READY"]}))


if __name__ == "__main__":
    main()
