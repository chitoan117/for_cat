"""Developer-only static/strict/native/contract/audit checks after normal regression."""
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.check_release import CheckFailure,execute


def main():
    folder=ROOT/".release"; folder.mkdir(exist_ok=True)
    summary={"schema_version":1,"status":"RUNNING","milestone":"M2","hardware":"NOT_VERIFIED","checks":{}}
    try:
        execute("ruff",[sys.executable,"-m","ruff","check","jetson/app","jetson/tools","ai","scripts"],ROOT,folder)
        summary["checks"]["ruff"]="PASS"
        execute("mypy",[sys.executable,"-m","mypy","--follow-imports","silent","--ignore-missing-imports",
            "ai/artifacts.py","ai/sampling.py","ai/session.py","jetson/app/vision/tracking.py","jetson/app/ai/service.py"],ROOT,folder)
        summary["checks"]["mypy_selected_5_files"]="PASS"
        zig=shutil.which("zig") or next((str(p) for p in sorted((ROOT/".tools-zig").glob("**/zig.exe"))),None)
        compiler=shutil.which("c++") if not zig else None
        if not zig and not compiler: raise CheckFailure("strict native compiler missing")
        prefix=[zig,"c++"] if zig else [compiler]
        for kind in ("safety","drivers"):
            binary=ROOT/".native-build"/f"native_{kind}_strict{'.exe' if sys.platform=='win32' else ''}"
            execute(f"strict-{kind}",[*prefix,"-std=c++17","-Wall","-Wextra","-Wpedantic","-Wconversion","-Wsign-conversion","-Wshadow","-Werror",
                f"-I{ROOT/'esp32/include'}",ROOT/f"esp32/test/native_{kind}.cpp","-o",binary],ROOT,folder)
            execute(f"strict-{kind}-run",[binary,*([ROOT/"docs/UART_V1_GOLDEN_VECTORS.csv"] if kind=="safety" else [])],ROOT,folder)
            summary["checks"][f"strict_{kind}"]="PASS"
        execute("openapi",[sys.executable,ROOT/"scripts/api_contract.py"],ROOT,folder)
        summary["checks"]["openapi"]="PASS"
        execute("audit",[sys.executable,ROOT/"scripts/release_audit.py","--write"],ROOT,folder)
        summary["checks"]["source_docs_audit"]="PASS"
        summary["status"]="PASSED_QUALITY_CHECKS"
    except (CheckFailure,OSError,ValueError) as exc:
        summary["status"]="FAILED"; summary["error"]=str(exc); print(str(exc))
    (folder/"quality_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2)); return summary["status"]!="PASSED_QUALITY_CHECKS"


if __name__=="__main__": sys.exit(main())
