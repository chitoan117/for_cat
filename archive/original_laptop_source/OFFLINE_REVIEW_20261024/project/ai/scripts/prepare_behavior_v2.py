"""Thin offline orchestration over existing import/extract/annotate/split/report modules."""
import argparse
import json
from pathlib import Path

from ai.artifacts import read_json, write_json
from ai.behavior_readiness import new_report_dir, readiness, write_reports
from ai.dataset import ID_PATTERN
from ai.scripts.extract_frames import extract
from ai.scripts.import_video import import_directory, load_sources
from ai.scripts.split_dataset import split
from ai.temporal_annotations import annotate_intervals


def extract_sessions(root, *, apply=False, max_frames=10000, blur_threshold=50, continue_on_error=False):
    results = []
    for source in load_sources(root):
        try:
            results.append(extract(source["source_video"], source["session_id"], root, apply=apply, resume=True,
                                   schema_version=2, interval_seconds=0.5, minimum_spacing=0.5,
                                   max_frames=max_frames, blur_threshold=blur_threshold))
        except (ValueError, OSError) as error:
            if not continue_on_error:
                raise
            results.append({"status": "EXTRACTION_FAILED", "session_id": source["session_id"], "error": str(error)})
    failed = any(item["status"] == "EXTRACTION_FAILED" for item in results)
    return {"status": "EXTRACTION_FAILED" if failed else "EXTRACTED_SESSIONS" if apply else "DRY_RUN", "sessions": results}


def annotation_template(root, session_id):
    if not session_id or not ID_PATTERN.fullmatch(session_id):
        raise ValueError("explicit valid --session-id required")
    source = next((item for item in load_sources(root) if item["session_id"] == session_id), None)
    if source is None:
        raise ValueError("unknown source session")
    return {"schema_version": 2, "session_id": session_id, "source_hash": source["source_hash"],
            "annotation_source": "HUMAN_REVIEW_REQUIRED", "reviewer": "", "intervals": [],
            "notes": "Watch the original video, fill start/end/label intervals, then explicitly set HUMAN_REVIEWED. No default IDLE/EATING."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "import", "extract", "sessions", "template", "annotate", "split", "report", "near-review-template"))
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--videos-dir", type=Path)
    parser.add_argument("--session-metadata", type=Path)
    parser.add_argument("--session-id")
    parser.add_argument("--intervals", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--boundary-seconds", type=float, default=0.25)
    parser.add_argument("--boundary-label", choices=("UNKNOWN", "UNSURE"), default="UNSURE")
    parser.add_argument("--max-frames", type=int, default=10000)
    parser.add_argument("--blur-threshold", type=float, default=50)
    parser.add_argument("--min-class-samples", type=int, default=10)
    parser.add_argument("--near-comparison-limit", type=int, default=2_000_000)
    parser.add_argument("--near-review", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = args.dataset_root
    try:
        result = {}
        if args.action in ("import", "prepare"):
            if args.videos_dir is None:
                raise ValueError("--videos-dir required")
            metadata = read_json(args.session_metadata) if args.session_metadata else None
            result["import"] = import_directory(args.videos_dir, root, apply=args.apply, metadata_document=metadata)
        if args.action == "extract" or (args.action == "prepare" and args.apply):
            result["extraction"] = extract_sessions(root, apply=args.apply, max_frames=args.max_frames, blur_threshold=args.blur_threshold, continue_on_error=True)
            if args.action == "extract":
                result["status"] = result["extraction"]["status"]
        if args.action == "sessions":
            result = {"sources": load_sources(root)}
        elif args.action == "template":
            result = annotation_template(root, args.session_id)
            if args.output and args.apply:
                write_json(args.output, result)
        elif args.action == "annotate":
            if not args.intervals:
                raise ValueError("--intervals required")
            result = annotate_intervals(root, args.intervals, session_id=args.session_id, apply=args.apply,
                                        replace=args.replace, boundary_seconds=args.boundary_seconds, boundary_label=args.boundary_label)
        elif args.action == "split":
            result = split(root, args.seed, apply=args.apply, refresh=args.refresh)
        elif args.action in ("report", "prepare", "near-review-template"):
            report = readiness(root, min_class_samples=args.min_class_samples, blur_threshold=args.blur_threshold,
                               near_comparison_limit=args.near_comparison_limit, near_review=args.near_review)
            if args.action == "near-review-template":
                result = {"schema_version": 1, "review_source": "HUMAN_REVIEW_REQUIRED", "notes": "",
                          "manifest_sha256": report["manifest_sha256"],
                          "reviewed_source_pairs": report["near_duplicates"]["cross_source_pairs"]}
                if args.output and args.apply:
                    write_json(args.output, result)
            else:
                result.update(report)
                if args.output_dir or args.apply:
                    result["report_files"] = write_reports(report, args.output_dir or new_report_dir(root))
                if args.action == "prepare" and not args.apply:
                    result["extraction"] = "NOT_RUN_FOR_UNIMPORTED_DRY_RUN_SOURCES"
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result.get("status") in ("NOT_READY", "EXTRACTION_FAILED") else 0
    except (ValueError, OSError) as error:
        parser.exit(2, f"BEHAVIOR_WORKFLOW_FAILED: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
