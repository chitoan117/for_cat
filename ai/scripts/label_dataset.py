"""Human annotation CLI: individual samples or explicit reviewed session intervals."""
import argparse
import json
from pathlib import Path

from ai.dataset import ROOT, BEHAVIOR_LABELS, IDENTITY_LABELS, load_manifest
from ai.label_schema import BEHAVIOR_V2, SUBJECT_V2, V2_REVIEW, v2_pair_error
from ai.manifest_io import dataset_lock, replace_manifest


def set_label(old, identity, behavior, *, subject=None, usable=True, replace=False):
    v2 = old.get("schema_version", 1) == 2
    if not replace and (old["identity_label"] is not None or old["behavior_label"] is not None or
                        (v2 and old.get("subject_label") is not None)):
        raise ValueError("already labeled; no silent overwrite (explicit --replace required)")
    if v2:
        if identity is not None or subject not in SUBJECT_V2 or behavior not in BEHAVIOR_V2 + V2_REVIEW:
            raise ValueError("schema v2 requires --subject and no --identity")
        usable = usable and subject == "CAT" and behavior in BEHAVIOR_V2
        problem = v2_pair_error(subject, behavior, usable)
        if problem:
            raise ValueError(problem)
        old.update(identity_label=None, subject_label=subject, behavior_label=behavior, usable=usable)
    else:
        if identity not in IDENTITY_LABELS or identity is None or behavior not in BEHAVIOR_LABELS or subject is not None:
            raise ValueError("invalid legacy identity or behavior label")
        old.update(identity_label=identity, behavior_label=behavior,
                   usable=usable and identity != "SKIP" and behavior != "SKIP")


def label(root: Path, sample_id: str, identity: str | None, behavior: str,
          *, usable=True, apply=False, subject=None, replace=False):
    with dataset_lock(root, apply):
        rows, errors = load_manifest(root)
        if errors:
            raise ValueError("invalid metadata: " + "; ".join(errors[:3]))
        matches = [row for row in rows if row["sample_id"] == sample_id]
        if not matches:
            raise ValueError("sample ID not found")
        old = matches[0]
        set_label(old, identity, behavior, subject=subject, usable=usable, replace=replace)
        if apply:
            replace_manifest(root, rows, action="HUMAN_SAMPLE_LABEL", details={"sample_id": sample_id, "replace": replace})
        return {"status": "LABELED" if apply else "DRY_RUN", "sample_id": sample_id,
                "identity_label": identity, "behavior_label": behavior, "usable": old["usable"],
                **({"schema_version": 2, "subject_label": subject} if old.get("schema_version") == 2 else {})}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_id", nargs="?")
    parser.add_argument("--identity", choices=sorted(x for x in IDENTITY_LABELS if x))
    parser.add_argument("--subject", choices=SUBJECT_V2)
    parser.add_argument("--behavior", choices=sorted((BEHAVIOR_LABELS - {None}) | set(BEHAVIOR_V2 + V2_REVIEW)))
    parser.add_argument("--session-id")
    parser.add_argument("--intervals", type=Path)
    parser.add_argument("--boundary-seconds", type=float, default=0.25)
    parser.add_argument("--boundary-label", choices=("UNKNOWN", "UNSURE"), default="UNSURE")
    parser.add_argument("--replace", action="store_true", help="explicit correction; interval mode replaces the WHOLE session annotation")
    parser.add_argument("--unusable", action="store_true")
    parser.add_argument("--dataset", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.intervals:
            from ai.temporal_annotations import annotate_intervals
            if args.sample_id or args.behavior or args.subject or args.identity:
                raise ValueError("choose sample labeling OR interval annotation")
            result = annotate_intervals(args.dataset, args.intervals, session_id=args.session_id, apply=args.apply,
                                        replace=args.replace, boundary_seconds=args.boundary_seconds,
                                        boundary_label=args.boundary_label)
        elif args.sample_id and args.behavior and not args.session_id:
            result = label(args.dataset, args.sample_id, args.identity, args.behavior, subject=args.subject,
                           usable=not args.unusable, apply=args.apply, replace=args.replace)
        else:
            raise ValueError("supply sample_id + --behavior, or --intervals")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"LABEL_FAILED: {exc}\n")
