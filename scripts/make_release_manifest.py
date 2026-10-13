"""Hash allowlisted source/docs and existing safe firmware; no flash/model/dataset data."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.check_release import PROFILES
from scripts.release_audit import source_files


def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def firmware_manifest():
    summary=json.loads((ROOT/".checks/summary.json").read_text(encoding="utf-8"))
    if summary["status"]!="PASSED_HOST_CHECKS": raise ValueError("successful full check required")
    log=(ROOT/".checks/firmware-builds.log").read_text(encoding="utf-8")
    entries=[]
    for profile in PROFILES:
        path=ROOT/f"esp32/.pio/build/{profile}/firmware.bin"
        if not path.is_file() or summary["checks"]["firmware"].get(profile)!="PASS": raise ValueError("missing successful firmware: "+profile)
        match=re.search(rf"Processing {re.escape(profile)}\b(.*?)(?=Processing |\Z)",log,re.S)
        if not match: raise ValueError("missing profile log")
        ram=re.search(r"RAM:.*?used (\d+) bytes from (\d+) bytes",match.group(1))
        flash=re.search(r"Flash:.*?used (\d+) bytes from (\d+) bytes",match.group(1))
        if not ram or not flash: raise ValueError("missing footprint for "+profile)
        entries.append({"profile":profile,"path":path.relative_to(ROOT).as_posix(),"firmware_size_bytes":path.stat().st_size,
            "sha256":sha256(path),"ram_used_bytes":int(ram[1]),"ram_limit_bytes":int(ram[2]),
            "flash_used_bytes":int(flash[1]),"application_partition_bytes":int(flash[2]),"flashed":False})
    return {"schema_version":1,"evidence":"PC COMPILE ONLY; hardware not verified","profiles":entries}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--verify",action="store_true"); a=p.parse_args()
    folder=ROOT/".release"; folder.mkdir(exist_ok=True)
    if a.verify:
        data=json.loads((folder/"release_manifest.json").read_text(encoding="utf-8")); failures=[]
        for entry in data["files"]:
            path=(ROOT/entry["path"]).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or sha256(path)!=entry["sha256"]:
                failures.append(entry["path"])
        print(json.dumps({"status":"PASS" if not failures else "FAIL","hash_mismatches":failures},indent=2)); return bool(failures)
    firmware=firmware_manifest()
    paths=source_files()+[ROOT/entry["path"] for entry in firmware["profiles"]]
    result={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"milestone":"M2",
        "files":[{"path":path.relative_to(ROOT).as_posix(),"size_bytes":path.stat().st_size,"sha256":sha256(path)} for path in sorted(set(paths))],
        "exclusions":"secrets/venvs/caches/datasets/models/evidence photos/private logs/factory images",
        "full_check":json.loads((ROOT/".checks/summary.json").read_text(encoding="utf-8"))}
    (folder/"firmware_manifest.json").write_text(json.dumps(firmware,indent=2)+"\n",encoding="utf-8")
    (folder/"release_manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"files":len(result["files"]),"firmware_profiles":len(firmware["profiles"]),"flashed":False},indent=2)); return 0


if __name__=="__main__": sys.exit(main())
