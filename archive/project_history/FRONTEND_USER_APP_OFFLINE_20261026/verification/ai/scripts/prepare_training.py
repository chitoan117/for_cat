"""Write future training configuration only with --apply; never train automatically."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT
from ai.training import LABEL_MAPS, prepare


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=sorted(LABEL_MAPS), required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.task, args.dataset, args.seed, args.patience)
    except ValueError as exc:
        parser.exit(2, f"TRAINING_PLAN_INVALID: {exc}\n")
    if args.apply and result["status"] == "READY_FOR_FUTURE_TRAINER":
        if args.output is None:
            parser.error("--output required with --apply")
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, indent=2))
