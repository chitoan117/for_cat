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
          "diag_water_sensor","diag_oled_button_buzzer")


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
    args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    logs=args.output or root/".checks"
    logs.mkdir(parents=True,exist_ok=True)
    summary={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"status":"RUNNING",
        "milestone":"M2","hardware":"NOT_VERIFIED","ai":"NOT_TRAINED","checks":{},
        "environment":{"python":platform.python_version(),"platform":platform.platform(),
          "packages":sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())}}
    exit_code=0
    try:
        summary["checks"]["python"]=pytest_counts(execute("python-tests",[sys.executable,"-m","pytest","-q"],root,logs))
        execute("imports",[sys.executable,"-c","import app.main, ai.capture, ai.experiments, app.analytics.reports; print('Import checks OK; no devices opened')"],root,logs)
        execute("dependencies",[sys.executable,"-m","pip","check"],root,logs)
        summary["checks"]["dataset"]=json.loads(execute("dataset",[sys.executable,"-m","ai.scripts.dataset_release","validate"],root,logs))
        zig=shutil.which("zig") or next((str(p) for p in sorted((root/".tools-zig").glob("**/zig.exe"))),None)
        compiler=shutil.which("c++") if not zig else None
        if not zig and not compiler: raise CheckFailure("native compiler unavailable: checks NOT RUN")
        command=[zig,"c++"] if zig else [compiler]
        build=root/".native-build"; build.mkdir(exist_ok=True)
        for kind in ("safety","drivers"):
            binary=build/f"native_{kind}{'.exe' if os.name=='nt' else ''}"
            execute(f"compile-{kind}",[*command,"-std=c++17","-Wall","-Wextra",*(["-Wno-nullability-completeness"] if zig else []),f"-I{root/'esp32/include'}",root/f"esp32/test/native_{kind}.cpp","-o",binary],root,logs)
            output=execute(f"native-{kind}",[binary,*([root/"docs/UART_V1_GOLDEN_VECTORS.csv"] if kind=="safety" else [])],root,logs)
            found=re.search(r"(\d+) (?:checks|assertions)",output)
            if not found: raise CheckFailure("native assertion count missing")
            summary["checks"][f"native_{kind}"]=int(found.group(1))
            if kind=="safety":
                if "7 UART v1 vectors match" not in output: raise CheckFailure("UART vector verification missing")
                summary["checks"]["uart_vectors"]=7
        guards=execute("compile-guards",[sys.executable,root/"scripts/test_safe_build_guards.py","--zig" if zig else "--compiler",zig or compiler],root,logs)
        match=re.search(r"(\d+)/(\d+) pass",guards)
        if not match or match.group(1)!=match.group(2): raise CheckFailure("compile guard summary missing/mismatched")
        summary["checks"]["compile_guards"]=int(match.group(1))
        local=root/(".tools-venv/Scripts/pio.exe" if os.name=="nt" else ".tools-venv/bin/pio")
        pio=str(local) if local.is_file() else shutil.which("pio")
        if not pio: raise CheckFailure("PlatformIO unavailable: builds NOT RUN")
        version=execute("platformio-version",[pio,"--version"],root,logs).strip()
        summary["environment"]["platformio"]=version
        output=execute("firmware-builds",[pio,"run",*(arg for profile in PROFILES for arg in ("-e",profile))],root,logs,cwd=root/"esp32",timeout=900)
        for profile in PROFILES:
            if not re.search(rf"^{re.escape(profile)}\s+SUCCESS\b",output,re.MULTILINE):
                raise CheckFailure(f"firmware summary missing SUCCESS: {profile}")
        summary["checks"]["firmware"]={profile:"PASS" for profile in PROFILES}
        summary["status"]="PASSED_HOST_CHECKS"
    except (CheckFailure,OSError,ValueError) as exc:
        exit_code=1; summary["status"]="FAILED"; summary["error"]=str(exc)
        print(f"FAILED: {exc}")
    finally:
        (logs/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        checks=summary["checks"]
        print(f"\nRELEASE CHECK: {summary['status']} | milestone M2 | hardware NOT VERIFIED | AI NOT TRAINED")
        print(f"Python: {checks.get('python','NOT RUN')} | C++: {checks.get('native_safety','NOT RUN')} safety + {checks.get('native_drivers','NOT RUN')} driver")
        print(f"UART: {checks.get('uart_vectors','NOT RUN')}/7 | guards: {checks.get('compile_guards','NOT RUN')} | firmware: {len(checks.get('firmware',{}))}/{len(PROFILES)}")
        print(f"Dataset: {checks.get('dataset',{}).get('status','NOT RUN')} | complete logs/summary: {logs}")
    return exit_code


if __name__=="__main__": sys.exit(main())
