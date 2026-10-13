# Supplied-prediction evaluation

`ai/evaluation.py` supports accuracy, per-class precision/recall/F1/support, confusion matrix, macro metrics and UNKNOWN rate. Empty inputs emit PREDICTIONS_NOT_AVAILABLE, with no invented scores. Ground truth must be a task's known class; prediction may be UNKNOWN after abstention. Undefined denominators remain null; macro values average defined per-class values only, with that policy recorded.

Identity reports separately count OTHER_CAT→OWNER_CAT false acceptance and OWNER_CAT→OTHER_CAT false rejection, dividing by all supplied actual OTHER_CAT or OWNER_CAT samples respectively (including abstained predictions). UNKNOWN is separately reported, not hidden as a correct identity. Include confusion/source/session details and class coverage before interpreting aggregates.

Event inputs have event_id, source session_id, optional track_id, label EATING/DRINKING and finite start/end media seconds. One-to-one highest-IoU greedy matching requires same source/label/track, positive interval overlap, configured start/end tolerances and minimum overlap. Reports matched overlap/boundary errors, false events, missed events and event precision/recall/F1. This deterministic matching is not an optimal assignment solver; split/merge episodes need human review. Legacy event-ID set arithmetic remains historical and is not a temporal evaluation substitute.

```text
python -m ai.scripts.evaluate_run frames --input SUPPLIED_PREDICTIONS.json --task identity
python -m ai.scripts.evaluate_run events --input SUPPLIED_EVENTS.json --start-tolerance REVIEWED_SECONDS --end-tolerance REVIEWED_SECONDS --minimum-overlap REVIEWED_FRACTION
python -m ai.scripts.evaluate_run sweep --input SUPPLIED_CONFIDENCES.json --task identity --thresholds REVIEWED_THRESHOLDS
```

Frames: list of actual/predicted labels, with confidence for sweeps. Events: object containing actual/predicted event lists. Sweep reports owner acceptance/other false acceptance/UNKNOWN through per-class metrics; behavior provides precision/recall/F1. No tool selects a production threshold. CLI report evidence is supplied predictions, not independently verified real-data validation; synthetic fixture arithmetic must never be cited as model accuracy.
