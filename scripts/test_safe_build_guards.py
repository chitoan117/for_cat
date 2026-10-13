"""Compile expected-invalid *host* configurations; never execute GPIO/device code."""

import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    compiler = parser.add_mutually_exclusive_group(required=True)
    compiler.add_argument("--zig", type=Path)
    compiler.add_argument("--compiler", type=Path)
    args = parser.parse_args()
    include = Path(__file__).resolve().parents[1] / "esp32" / "include"
    cases = [([], True), (["-DACTUATOR_OUTPUTS_ENABLED=1"], False),
             (["-DFORR_BOARD_CLASSIC=1", "-DFORR_BOARD_S3=1"], False),
             (["-DFORR_NATIVE_USB=1", "-DFORR_BOARD_S3=1"], False),
             (["-DSIMULATED_SENSORS=1", "-DFORR_HW_SAFE=1"], False),
             (["-DSERVO_DIAGNOSTIC_ENABLED=1"], False),
             (["-DPUMP_DIAGNOSTIC_ENABLED=1"], False),
             (["-DM4_DIAGNOSTIC_MODE=1"], False),
             (["-DM4_DIAGNOSTIC_MODE=7", "-DFORR_HW_SAFE=1"], False),
             (["-DM4_DIAGNOSTIC_MODE=1", "-DFORR_HW_SAFE=1", "-DSIMULATED_SENSORS=1"], False),
             (["-DM4_PINS_REVIEWED=2"], False),
             (["-DM4_BUTTON_PULL=3"], False)]
    cases.extend(([f"-DM4_DIAGNOSTIC_MODE={mode}", "-DFORR_HW_SAFE=1"], True) for mode in range(1, 7))
    command = [str(args.zig), "c++"] if args.zig else [str(args.compiler)]
    with tempfile.TemporaryDirectory(prefix="forr-cat-guard-") as work:
        source = Path(work) / "guard.cpp"
        source.write_text('#include "board_config.h"\n#include "pins.h"\n'
                          '#include "m4/diagnostic_config.h"\n#include "m4/actuator_interfaces.h"\n', encoding="utf-8")
        for index, (defines, expected) in enumerate(cases):
            result = subprocess.run([*command, "-std=c++17", f"-I{include}",
                                     *defines, "-c", str(source), "-o", str(Path(work) / f"{index}.o")],
                                    capture_output=True, text=True, timeout=30)
            if (result.returncode == 0) != expected:
                raise RuntimeError(f"safety guard case {index} incorrect: {result.stderr}")
    print(f"HOST compile guards: {len(cases)}/{len(cases)} pass (including six valid unassigned diagnostics and rejected actuator/SIM/invalid configurations)")


if __name__ == "__main__":
    main()
