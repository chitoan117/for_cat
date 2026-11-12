import argparse
import json
from pathlib import Path
from ai.artifacts import read_json
from ai.public_data import validate_provenance


def main():
    parser=argparse.ArgumentParser(description="Review a supplied public-source provenance manifest offline; no download")
    parser.add_argument("--manifest",type=Path,required=True); args=parser.parse_args()
    try: result=validate_provenance(read_json(args.manifest))
    except (OSError,ValueError) as exc: parser.exit(2,"PROVENANCE_FAILED: "+str(exc)+"\n")
    print(json.dumps(result,indent=2)); return 2 if result["errors"] else 0


if __name__=="__main__": raise SystemExit(main())
