"""Deterministic JSON quality report, including an empty-dataset status."""

import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="exclusive-create; never overwrite")
    args = parser.parse_args()
    result = report(args.dataset)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    print(text)
