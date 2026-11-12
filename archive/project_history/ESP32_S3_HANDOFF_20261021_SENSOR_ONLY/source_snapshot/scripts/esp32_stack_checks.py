"""Release-runner extension: native bridge/fuzz + process-level real-stack tests."""
import json
import os
import sys


def run(root, logs, compiler, execute, zig=False, sanitizer=None):
    build = root / ".native-build"
    suffix = ".exe" if os.name == "nt" else ""
    flags = ["-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror",
             "-Wno-unused-variable", "-fno-omit-frame-pointer"]
    if zig:
        flags += ["-Wno-nullability-completeness"]
    if sanitizer:
        flags += ["-fsanitize=" + sanitizer]
    binaries = {}
    for name, defines in (("protocol", []), ("ascii", ["-DHOST_ASCII=1"]),
                          ("absent", ["-DHOST_ASCII=1", "-DHOST_HX_INSTALLED=0"])):
        binary = build / ("stack_" + name + suffix)
        execute("compile-stack-" + name, [*compiler, *flags, *defines,
                "-I" + str(root / "esp32/test/arduino_stub"), "-I" + str(root / "esp32/include"),
                root / "esp32/test/firmware_bridge.cpp", "-o", binary], root, logs)
        binaries[name] = binary
    fuzz = build / ("protocol_fuzz" + suffix)
    execute("compile-protocol-fuzz", [*compiler, *flags, "-I" + str(root / "esp32/test/arduino_stub"),
            "-I" + str(root / "esp32/include"), root / "esp32/test/protocol_fuzz.cpp", "-o", fuzz], root, logs)
    fuzz_output = execute("protocol-fuzz", [fuzz, "2000"], root, logs)
    fuzz_result = json.loads(fuzz_output)
    if fuzz_result["result"] != "PASS" or fuzz_result["iterations"] != 2000:
        raise ValueError("native parser fuzz did not pass")
    from datetime import datetime, timezone
    output = logs / ("stack-e2e-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    execute("stack-e2e", [sys.executable, root / "scripts/test_esp32_stack.py", "--protocol", binaries["protocol"],
            "--ascii", binaries["ascii"], "--absent", binaries["absent"], "--output", output], root, logs, timeout=180)
    result = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    if result["result"] != "PASS":
        raise ValueError("bidirectional process E2E did not pass")
    return {"process_e2e": result, "native_fuzz": fuzz_result, "evidence_directory": str(output)}
