"""Validation with explicit missing-data status and corruption/duplicate checks."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT)
    args = parser.parse_args()
    result = report(args.dataset)
    print(json.dumps(result, indent=2))
    if result["status"] == "DATASET_INVALID":
        parser.exit(2)
