"""Explicit OpenAPI export/check. No startup, camera, serial or on-disk DB."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"jetson"))


def current_schema():
    from app.main import create_app
    from app.storage.event_store import InMemoryEventStore
    app=create_app(store=InMemoryEventStore())
    try: return app.openapi()
    finally:
        app.state.observations.stop()
        app.state.records.close(); app.state.store.close()


def breaking_changes(old,new,path=""):
    """Conservative backward-contract check: descriptive metadata/additive keys are allowed."""
    failures=[]
    if isinstance(old,dict):
        if not isinstance(new,dict): return [path+": changed object type"]
        for key,value in old.items():
            if key in ("description","title","summary","example","examples"): continue
            if key not in new: failures.append(path+"/"+key+": removed")
            else: failures.extend(breaking_changes(value,new[key],path+"/"+key))
    elif isinstance(old,list):
        if not isinstance(new,list): return [path+": changed list type"]
        # Enum/required/anyOf/parameters must remain intact; additions need review if mandatory.
        if old!=new: failures.append(path+": changed contract list")
    elif old!=new: failures.append(path+": changed contract value")
    return failures


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--write",action="store_true")
    a=p.parse_args(); snapshot=ROOT/"docs/openapi_v1.json"; current=current_schema()
    if a.write:
        with snapshot.open("x",encoding="utf-8") as stream: json.dump(current,stream,indent=2,sort_keys=True)
        print("OpenAPI v1 snapshot created; no devices/DB file opened"); return 0
    old=json.loads(snapshot.read_text(encoding="utf-8")); failures=breaking_changes(old,current)
    print(json.dumps({"status":"PASS" if not failures else "FAIL","breaking_changes":failures,"public_paths":len(current["paths"])},indent=2))
    return bool(failures)


if __name__=="__main__": sys.exit(main())
