"""Dataset gates/releases, explicit session ingestion and optional local interchange."""
import argparse
import json
from pathlib import Path

from ai.dataset import ROOT
from ai.interchange import export, import_export
from ai.releases import acceptance, create_release, ingest_sessions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("validate","release","ingest","export","import"))
    p.add_argument("--dataset",type=Path,default=ROOT)
    p.add_argument("--output",type=Path)
    p.add_argument("--source",type=Path,nargs="*")
    p.add_argument("--version")
    p.add_argument("--task",choices=("identity","behavior"),default="identity")
    p.add_argument("--stage",choices=("PILOT_DATASET","TRAINING_CANDIDATE","TEST_CANDIDATE"),default="PILOT_DATASET")
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    try:
        if a.action=="validate": result=acceptance(a.dataset,task=a.task,stage=a.stage)
        elif a.output is None: raise ValueError("explicit --output required")
        elif a.action=="release": result=create_release(a.dataset,a.version or "",a.output,apply=a.apply,task=a.task,stage=a.stage)
        elif a.action=="ingest": result=ingest_sessions(a.source or [],a.output,apply=a.apply)
        elif a.action=="export": result=export(a.dataset,a.output,task=a.task,apply=a.apply)
        else:
            if not a.source or len(a.source)!=1: raise ValueError("one --source folder required")
            result=import_export(a.source[0],a.output,apply=a.apply)
        print(json.dumps(result,indent=2))
        if result.get("status") in ("REJECTED","SESSION_METADATA_MISSING"): p.exit(2)
    except (ValueError,OSError) as exc: p.exit(2,f"DATASET_OPERATION_FAILED: {exc}\n")


if __name__=="__main__": main()
