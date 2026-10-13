"""Metrics from supplied real predictions only; no numeric output without inputs."""

from ai.training import LABEL_MAPS
import math
from statistics import mean


def evaluate(rows: list[dict], task: str) -> dict:
    if task not in LABEL_MAPS:
        raise ValueError("unknown task")
    if not rows:
        return {"status": "PREDICTIONS_NOT_AVAILABLE"}
    classes = LABEL_MAPS[task]
    outputs = classes + ["UNKNOWN"]
    matrix = {actual: {predicted: 0 for predicted in outputs} for actual in classes}
    for row in rows:
        if not isinstance(row, dict) or row.get("actual") not in classes or row.get("predicted") not in outputs:
            raise ValueError("invalid prediction labels")
        matrix[row["actual"]][row["predicted"]] += 1
    total = len(rows)
    per_class = {}
    for label in classes:
        tp = matrix[label][label]
        predicted = sum(matrix[actual][label] for actual in classes)
        actual = sum(matrix[label].values())
        precision = tp / predicted if predicted else None
        recall = tp / actual if actual else None
        f1 = (2 * precision * recall / (precision + recall) if precision + recall else 0.0) \
             if precision is not None and recall is not None else None
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": actual}
    result = {"status": "EVALUATED_SUPPLIED_PREDICTIONS", "task": task, "samples": total,
              "accuracy": sum(matrix[x][x] for x in classes) / total,
              "confusion_matrix": matrix, "per_class": per_class}
    for metric in ("precision", "recall", "f1"):
        values = [entry[metric] for entry in per_class.values() if entry[metric] is not None]
        result["macro_"+metric] = mean(values) if values else None
    result["macro_policy"] = "defined per-class values only; absent denominators remain null"
    result["unknown_rate"] = sum(matrix[x]["UNKNOWN"] for x in classes)/total
    if task == "identity":
        other = sum(matrix["OTHER_CAT"].values())
        result["other_cat_to_owner_false_acceptance_rate"] = (
            matrix["OTHER_CAT"]["OWNER_CAT"] / other if other else None
        )
        result["other_cat_to_owner_false_acceptance_count"] = matrix["OTHER_CAT"]["OWNER_CAT"]
        result["other_cat_test_count"] = other
        owner = sum(matrix["OWNER_CAT"].values())
        rejected = matrix["OWNER_CAT"]["OTHER_CAT"]
        result["owner_cat_to_other_false_rejection_count"] = rejected
        result["owner_cat_to_other_false_rejection_rate"] = rejected/owner if owner else None
        result["owner_cat_test_count"] = owner
        result["owner_acceptance_rate"] = matrix["OWNER_CAT"]["OWNER_CAT"]/owner if owner else None
    else:
        # Optional event-level set matching requires caller-supplied event_id.
        events = [r for r in rows if r.get("event_id") is not None]
        if events:
            if any(not isinstance(r["event_id"], (int, str)) or len(str(r["event_id"])) > 64
                   for r in events):
                raise ValueError("invalid event ID")
            true = {(r["event_id"], r["actual"]) for r in events}
            predicted = {(r["event_id"], r["predicted"]) for r in events}
            overlap = len(true & predicted)
            result["event_level_precision"] = overlap / len(predicted) if predicted else None
            result["event_level_recall"] = overlap / len(true) if true else None
    return result


def threshold_sweep(rows, task, thresholds):
    if task not in LABEL_MAPS or not 1 <= len(thresholds) <= 101 or any(not math.isfinite(t) or not 0 <= t <= 1 for t in thresholds):
        raise ValueError("invalid sweep")
    if not rows:
        return {"status": "PREDICTIONS_NOT_AVAILABLE", "selected_production_threshold": None}
    for row in rows:
        if not isinstance(row,dict) or row.get("predicted") not in LABEL_MAPS[task] or not isinstance(row.get("confidence"),(int,float)) or not math.isfinite(row["confidence"]) or not 0 <= row["confidence"] <= 1:
            raise ValueError("sweep requires valid supplied label/confidence")
    results = []
    for threshold in sorted(set(thresholds)):
        evaluated = evaluate([{**row,"predicted": row["predicted"] if row["confidence"] >= threshold else "UNKNOWN"} for row in rows],task)
        results.append({"threshold": threshold, **evaluated})
    return {"status": "EVALUATED_SUPPLIED_PREDICTIONS", "task": task, "results": results,
            "selected_production_threshold": None, "usage": "validation only; never optimize on final test set"}


def evaluate_events(actual, predicted, *, start_tolerance=1.0, end_tolerance=1.0, minimum_overlap=0.5):
    if any(not math.isfinite(x) or x < 0 for x in (start_tolerance,end_tolerance)) or not math.isfinite(minimum_overlap) or not 0 <= minimum_overlap <= 1:
        raise ValueError("invalid event tolerance")
    if not actual and not predicted:
        return {"status": "EVENTS_NOT_AVAILABLE"}
    if len(actual)>1000 or len(predicted)>1000:
        raise ValueError("event matching budget exceeded")
    for rows in (actual,predicted):
        seen=set()
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get("event_id"),str) or not 1 <= len(row["event_id"]) <=64 or row["event_id"] in seen or row.get("label") not in ("EATING","DRINKING") or not isinstance(row.get("session_id"),str) or not row["session_id"]:
                raise ValueError("invalid/duplicate event identity")
            seen.add(row["event_id"])
            start,end=row.get("start"),row.get("end")
            if any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in (start,end)) or end<=start:
                raise ValueError("finite positive event interval required")
    candidates=[]
    for i,a in enumerate(actual):
        for j,p in enumerate(predicted):
            if (a["session_id"],a["label"],a.get("track_id")) != (p["session_id"],p["label"],p.get("track_id")):
                continue
            overlap=max(0,min(a["end"],p["end"])-max(a["start"],p["start"]))
            union=max(a["end"],p["end"])-min(a["start"],p["start"])
            iou=overlap/union
            if overlap>0 and abs(a["start"]-p["start"])<=start_tolerance and abs(a["end"]-p["end"])<=end_tolerance and iou>=minimum_overlap:
                candidates.append((-iou,i,j))
    # Deterministic highest-overlap greedy one-to-one matching; never match across source session/track.
    used_a,used_p,matches=set(),set(),[]
    for negative,i,j in sorted(candidates):
        if i not in used_a and j not in used_p:
            used_a.add(i); used_p.add(j)
            matches.append({"actual": actual[i]["event_id"], "predicted": predicted[j]["event_id"], "overlap": -negative,
                "start_error": predicted[j]["start"]-actual[i]["start"], "end_error": predicted[j]["end"]-actual[i]["end"]})
    precision=len(matches)/len(predicted) if predicted else None
    recall=len(matches)/len(actual) if actual else None
    return {"status": "EVALUATED_SUPPLIED_EVENTS", "matching": "highest-overlap greedy one-to-one",
        "precision": precision,"recall": recall,"f1": 2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0 if precision is not None and recall is not None else None,
        "matches": matches,"false_events": [p["event_id"] for j,p in enumerate(predicted) if j not in used_p],
        "missed_events": [a["event_id"] for i,a in enumerate(actual) if i not in used_a],
        "tolerances": {"start_seconds": start_tolerance,"end_seconds": end_tolerance,"minimum_overlap": minimum_overlap}}
