import argparse
import json
from pathlib import Path
from ai.artifacts import read_json
from ai.experiments import candidates, prepare_bundle, register_model, archive_result


def main():
    p=argparse.ArgumentParser(description="Offline experiment preparation / inactive model registration; no training")
    p.add_argument("action",choices=("candidates","prepare","register","archive"))
    p.add_argument("--config",type=Path); p.add_argument("--release",type=Path)
    p.add_argument("--output",type=Path); p.add_argument("--artifact-root",type=Path)
    p.add_argument("--expected-task",choices=("detector","identity","behavior"))
    p.add_argument("--metrics",type=Path); p.add_argument("--evaluation",type=Path); p.add_argument("--artifact-name")
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    try:
        if a.action=="candidates": result={"candidates":candidates(),"downloaded":False}
        elif not a.config or not a.output: raise ValueError("--config and --output required")
        elif a.action=="prepare":
            if not a.release: raise ValueError("--release required")
            result=prepare_bundle(read_json(a.config),read_json(a.release),a.output,apply=a.apply)
        elif a.action=="archive":
            if not a.metrics or not a.evaluation or not a.artifact_root or not a.artifact_name: raise ValueError("metrics, evaluation, artifact root/name required")
            result=archive_result(read_json(a.config),read_json(a.metrics),read_json(a.evaluation),a.artifact_root,a.artifact_name,a.output,apply=a.apply)
        else:
            if not a.artifact_root or not a.expected_task: raise ValueError("artifact root and expected task required")
            result=register_model(read_json(a.config),a.artifact_root,a.output,expected_task=a.expected_task,apply=a.apply)
        print(json.dumps(result,indent=2))
    except (ValueError,OSError) as exc: p.exit(2,f"EXPERIMENT_OPERATION_FAILED: {exc}\n")


if __name__=="__main__": main()
