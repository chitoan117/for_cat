import argparse
import json
from pathlib import Path
from ai.artifacts import read_json, write_json
from ai.evaluation import evaluate, evaluate_events, threshold_sweep


def main():
    p=argparse.ArgumentParser(description="Evaluate supplied annotations/predictions only; never select a production threshold")
    p.add_argument("action",choices=("frames","events","sweep","shadow"))
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--task",choices=("identity","behavior"),default="identity")
    p.add_argument("--thresholds",type=float,nargs="+",default=[0.25,0.5,0.75])
    p.add_argument("--start-tolerance",type=float,default=1)
    p.add_argument("--end-tolerance",type=float,default=1)
    p.add_argument("--minimum-overlap",type=float,default=0.5)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    try:
        data=read_json(a.input)
        if a.action=="events": result=evaluate_events(data["actual"],data["predicted"],start_tolerance=a.start_tolerance,end_tolerance=a.end_tolerance,minimum_overlap=a.minimum_overlap)
        elif a.action=="sweep": result=threshold_sweep(data,a.task,a.thresholds)
        else: result=evaluate(data,a.task)
        result={**result,"evidence":"SUPPLIED_PREDICTIONS_NOT_INDEPENDENTLY_VERIFIED","actuation_enabled":False,"production_threshold_selected":False}
        if a.output: write_json(a.output,result)
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc: p.exit(2,f"EVALUATION_FAILED: {exc}\n")


if __name__=="__main__": main()
