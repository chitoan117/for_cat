"""Evaluate explicitly supplied JSON predictions (never synthesize accuracy)."""

import argparse
import json
from pathlib import Path

from ai.evaluation import evaluate
from ai.training import LABEL_MAPS


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=sorted(LABEL_MAPS))
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    if not args.predictions.is_file():
        print(json.dumps({"status": "PREDICTIONS_NOT_AVAILABLE"}))
    else:
        try:
            if args.predictions.stat().st_size > 10_000_000:
                raise ValueError("prediction file exceeds 10 MB")
            data = json.loads(args.predictions.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("prediction file must be an array")
            print(json.dumps(evaluate(data, args.task), indent=2))
        except (ValueError, UnicodeError) as exc:
            parser.exit(2, f"EVALUATION_FAILED: {exc}\n")
