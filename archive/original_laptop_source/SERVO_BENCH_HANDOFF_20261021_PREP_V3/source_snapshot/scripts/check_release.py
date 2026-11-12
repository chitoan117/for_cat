"""One-command host verification with truthful summary and full per-step logs. No devices."""
import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

PROFILES=("esp32dev_sim","esp32dev_hw_safe","esp32s3_n16r8_sim","esp32s3_n16r8_hw_safe",
          "esp32s3_n16r8_hw_safe_uart","diag_hx711","diag_rtc","diag_i2c","diag_food_sensor",
          "diag_water_sensor","diag_oled_button_buzzer","esp32s3_16mb_no_psram_hw_safe_uart",
          "diag_all_sensors","diag_hx711_surrogate","diag_rtc_surrogate","diag_i2c_surrogate",
          "diag_food_sensor_surrogate","diag_water_sensor_surrogate","diag_oled_button_buzzer_surrogate","esp32dev",
          "diag_approach_sensor","diag_servo_bench")


class CheckFailure(RuntimeError):
    pass


def pytest_counts(output):
    counts={key:int(match.group(1)) if (match:=re.search(rf"(\d+) {key}\b",output)) else 0
            for key in ("passed","failed","skipped","errors")}
    if not counts["passed"] or counts["failed"] or counts["errors"]:
        raise CheckFailure("pytest did not report a passing suite")
    return counts


def execute(name, command, root, logs, *, cwd=None, timeout=180):
    environment={**os.environ,"PYTHONIOENCODING":"utf-8","PYTHONPATH":os.pathsep.join((str(root/"jetson"),str(root)))}
    try:
        result=subprocess.run(list(map(str,command)),cwd=cwd or root,env=environment,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or b""
        if isinstance(output,bytes): output=output.decode("utf-8",errors="replace")
        (logs/f"{name}.log").write_text(output,encoding="utf-8")
        print(output)
        raise CheckFailure(f"{name}: timeout, check failed") from exc
    (logs/f"{name}.log").write_text(result.stdout,encoding="utf-8")
    if result.returncode:
        print(result.stdout)
        raise CheckFailure(f"{name}: exit {result.returncode}; full log {logs/name}.log")
    print(f"PASS {name}")
    return result.stdout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--fast",action="store_true",help="All software/protocol tests; skip only PlatformIO compile matrix")
    parser.add_argument("--compiler",type=Path,help="Existing native compiler/zig executable")
    parser.add_argument("--pio",type=Path,help="Existing PlatformIO executable, no toolchain installation")
    parser.add_argument("--sanitize",choices=("undefined","address,undefined"),help="Native sanitizers, runtime canary required")
    args=parser.parse_args()
    sanitizer_flags=["-fsanitize="+args.sanitize,"-fno-omit-frame-pointer"] if args.sanitize else []
    if args.sanitize:
        os.environ["ASAN_OPTIONS"]="detect_leaks="+("0" if os.name=="nt" else "1")+":halt_on_error=1"
        os.environ["UBSAN_OPTIONS"]="halt_on_error=1:print_stacktrace=1"
    root=Path(__file__).resolve().parent.parent
    logs=args.output or root/".checks"
    logs.mkdir(parents=True,exist_ok=True)
    summary={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"status":"RUNNING",
        "milestone":"HOST_SOFTWARE_VALIDATION","hardware":"PHYSICAL_NOT_TESTED",
        "ai":"NOT_EVALUATED_BY_THIS_CHECKER","dataset_scope":"REPOSITORY_DEFAULT_ONLY_NOT_EXTERNAL_CORPORA","checks":{},
        "environment":{"python":platform.python_version(),"platform":platform.platform(),
          "packages":sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())}}
    exit_code=0
    try:
        summary["checks"]["python"]=pytest_counts(execute("python-tests",[sys.executable,"-m","pytest","-q"],root,logs))
        execute("imports",[sys.executable,"-c","import app.main, ai.capture, ai.experiments, app.analytics.reports; print('Import checks OK; no devices opened')"],root,logs)
        execute("dependencies",[sys.executable,"-m","pip","check"],root,logs)
        summary["checks"]["dataset"]=json.loads(execute("dataset",[sys.executable,"-m","ai.scripts.dataset_release","validate"],root,logs))
        explicit=str(args.compiler) if args.compiler else None
        zig=(explicit if explicit and Path(explicit).stem=="zig" else None) or (None if explicit else shutil.which("zig") or next((str(p) for p in sorted((root/".tools-zig").glob("**/zig.exe"))),None))
        compiler=explicit if explicit and not zig else shutil.which("c++") if not zig else None
        if not zig and not compiler: raise CheckFailure("native compiler unavailable: checks NOT RUN")
        command=[zig,"c++"] if zig else [compiler]
        build=root/".native-build"; build.mkdir(exist_ok=True)
        if args.sanitize:
            canary=build/("sanitizer_canary"+(".exe" if os.name=="nt" else ""))
            execute("compile-sanitizer-canary",[*command,"-O1","-g",*sanitizer_flags,
                    root/"esp32/test/sanitizer_canary.cpp","-o",canary],root,logs)
            for mode in (["ubsan","asan"] if "address" in args.sanitize else ["ubsan"]):
                probe=subprocess.run([str(canary),mode],capture_output=True,timeout=30)
                text=(probe.stdout+probe.stderr).decode("utf-8","replace")
                (logs/(mode+"-canary.log")).write_text(text,encoding="utf-8")
                token="AddressSanitizer" if mode=="asan" else "signed integer overflow"
                if probe.returncode==0 or token not in text:
                    raise CheckFailure(mode+" instrumentation is unavailable/unverified; no sanitizer PASS may be claimed")
            summary["checks"]["sanitizer_runtime_canary"]="VERIFIED"
        for kind in ("safety","drivers"):
            binary=build/f"native_{kind}{'.exe' if os.name=='nt' else ''}"
            execute(f"compile-{kind}",[*command,"-std=c++17","-Wall","-Wextra",*sanitizer_flags,*(["-Wno-nullability-completeness"] if zig else []),f"-I{root/'esp32/include'}",root/f"esp32/test/native_{kind}.cpp","-o",binary],root,logs)
            output=execute(f"native-{kind}",[binary,*([root/"docs/UART_V1_GOLDEN_VECTORS.csv"] if kind=="safety" else [])],root,logs)
            found=re.search(r"(\d+) (?:checks|assertions)",output)
            if not found: raise CheckFailure("native assertion count missing")
            summary["checks"][f"native_{kind}"]=int(found.group(1))
            if kind=="safety":
                if "7 UART v1 vectors match" not in output: raise CheckFailure("UART vector verification missing")
                summary["checks"]["uart_vectors"]=7
        loop_binary=build/f"firmware_loop{'.exe' if os.name=='nt' else ''}"
        loop_evidence=logs/("firmware-loop-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        execute("compile-firmware-loop",[*command,"-std=c++17","-O1",*sanitizer_flags,"-Wall","-Wextra","-Wpedantic","-Wshadow","-Werror",
                "-Wno-unused-variable",*(["-Wno-nullability-completeness"] if zig else []),
                f"-I{root/'esp32/test/arduino_stub'}",f"-I{root/'esp32/include'}",
                root/"esp32/test/firmware_loop.cpp","-o",loop_binary],root,logs)
        execute("firmware-loop",[sys.executable,root/"scripts/test_firmware_loop.py","--binary",loop_binary,
                "--output",loop_evidence],root,logs)
        loop_result=json.loads((loop_evidence/"summary.json").read_text(encoding="utf-8"))
        if loop_result.get("result")!="PASS" or loop_result.get("physical_hardware_used") is not False:
            raise CheckFailure("firmware-loop result/scope mismatch")
        summary["checks"]["firmware_loop"]={key:loop_result[key] for key in
            ("named_cases","cpp_assertions","decoded_firmware_reports","physical_hardware_used")}
        summary["checks"]["firmware_loop"]["evidence_directory"]=str(loop_evidence)
        servo_binary=build/f"servo_bench_loop{'.exe' if os.name=='nt' else ''}"
        servo_evidence=logs/("servo-bench-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        execute("compile-servo-bench-loop",[*command,"-std=c++17","-O1",*sanitizer_flags,
                "-Wall","-Wextra","-Wpedantic","-Wshadow","-Werror","-Wno-unused-variable",
                *(["-Wno-nullability-completeness"] if zig else []),
                f"-I{root/'esp32/test/arduino_stub'}",f"-I{root/'esp32/include'}",
                root/"esp32/test/servo_bench_loop.cpp","-o",servo_binary],root,logs)
        execute("servo-bench-loop",[sys.executable,root/"scripts/test_servo_bench.py",
                "--binary",servo_binary,"--output",servo_evidence],root,logs)
        servo_result=json.loads((servo_evidence/"summary.json").read_text(encoding="utf-8"))
        if servo_result.get("named_cases")!=8 or servo_result.get("physical_validation")!="NOT_TESTED":
            raise CheckFailure("servo bench host scope mismatch")
        summary["checks"]["servo_bench"]={"named_cases":servo_result["named_cases"],
            "assertions":servo_result["assertions"],"physical_validation":"NOT_TESTED",
            "evidence_directory":str(servo_evidence)}
        from scripts.esp32_stack_checks import run as stack_checks
        summary["checks"]["bidirectional_stack"]=stack_checks(root,logs,command,execute,bool(zig),args.sanitize)
        summary["checks"]["sanitizer_scope"]={"native":args.sanitize or "none","leak_detection":bool(args.sanitize and os.name!="nt"),
            "tsan":"NOT_APPLICABLE_SINGLE_OWNER_CPP_PROCESSES"}
        guards=execute("compile-guards",[sys.executable,root/"scripts/test_safe_build_guards.py","--zig" if zig else "--compiler",zig or compiler],root,logs)
        match=re.search(r"(\d+)/(\d+) pass",guards)
        if not match or match.group(1)!=match.group(2): raise CheckFailure("compile guard summary missing/mismatched")
        summary["checks"]["compile_guards"]=int(match.group(1))
        local=root/(".tools-venv/Scripts/pio.exe" if os.name=="nt" else ".tools-venv/bin/pio")
        pio=str(args.pio) if args.pio else str(local) if local.is_file() else shutil.which("pio")
        if args.fast:
            summary["status"]="PASSED_FAST_SOFTWARE_CHECKS"
            summary["checks"]["firmware_compile_scope"]="NOT_RUN_FAST_MODE"
            return 0
        if not pio: raise CheckFailure("PlatformIO unavailable: builds NOT RUN")
        version=execute("platformio-version",[pio,"--version"],root,logs).strip()
        summary["environment"]["platformio"]=version
        output=execute("firmware-builds",[pio,"run",*(arg for profile in PROFILES for arg in ("-e",profile))],root,logs,cwd=root/"esp32",timeout=900)
        for profile in PROFILES:
            if not re.search(rf"^{re.escape(profile)}\s+SUCCESS\b",output,re.MULTILINE):
                raise CheckFailure(f"firmware summary missing SUCCESS: {profile}")
        summary["checks"]["firmware"]={profile:"PASS" for profile in PROFILES}
        from scripts.esp32_build_manifest import generate
        summary["checks"]["build_manifest"]=str(generate(root,logs,pio,PROFILES,output))
        summary["status"]="PASSED_HOST_CHECKS"
    except (CheckFailure,OSError,ValueError) as exc:
        exit_code=1; summary["status"]="FAILED"; summary["error"]=str(exc)
        print(f"FAILED: {exc}")
    finally:
        (logs/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        checks=summary["checks"]
        print(f"\nRELEASE CHECK: {summary['status']} | HOST SOFTWARE | PHYSICAL NOT TESTED | AI not evaluated by this checker")
        print(f"Python: {checks.get('python','NOT RUN')} | C++: {checks.get('native_safety','NOT RUN')} safety + {checks.get('native_drivers','NOT RUN')} driver")
        print(f"UART: {checks.get('uart_vectors','NOT RUN')}/7 | guards: {checks.get('compile_guards','NOT RUN')} | firmware: {len(checks.get('firmware',{}))}/{len(PROFILES)}")
        print(f"Offline firmware loop: {checks.get('firmware_loop','NOT RUN')} (host adapters, never physical PASS)")
        print(f"Dataset: {checks.get('dataset',{}).get('status','NOT RUN')} | complete logs/summary: {logs}")
    return exit_code


if __name__=="__main__": sys.exit(main())
