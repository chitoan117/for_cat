"""Never infer weight consumed unless stable validated pre/post sensor samples exist."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from statistics import mean

from app.behavior.temporal import SessionSignal, SignalType
from app.behavior.models import Behavior
from app.storage.records import BehaviorRecord, DrinkingSession, FeedingSession
from app.storage.repositories import RecordRepository
from app.ai.models import Identity


@dataclass(frozen=True)
class WeightSample:
    grams: float
    validated: bool
    sampled_at: datetime | None = None


def stable_weight(samples: list[WeightSample], tolerance_grams: float = 0.5) -> float | None:
    if len(samples) < 3 or any(not s.validated or not 0 <= s.grams <= 10000 for s in samples):
        return None
    values = [s.grams for s in samples]
    if max(values) - min(values) > tolerance_grams:
        return None
    return round(mean(values), 3)


def estimate_consumed(start: SessionSignal, end: SessionSignal,
                      before: list[WeightSample], after: list[WeightSample], *,
                       food_added_during_session: bool = False, max_age_seconds: float = 5) -> float | None:
    if food_added_during_session:
        return None
    if any(value is None or value.tzinfo is None or value.utcoffset() is None for value in (start.started_at,end.ended_at)):
        return None
    if start.signal != SignalType.START or end.signal != SignalType.END or \
            start.session_id != end.session_id or start.behavior.value != "EATING" or \
            start.identity not in (Identity.OWNER_CAT, Identity.OTHER_CAT) or start.identity != end.identity or \
            start.behavior != end.behavior or end.ended_at is None or end.ended_at < start.started_at or \
            not isfinite(max_age_seconds) or max_age_seconds <= 0:
        return None
    for samples, reference, preceding in ((before, start.started_at, True), (after, end.ended_at, False)):
        if any(s.sampled_at is None or s.sampled_at.tzinfo is None or s.sampled_at.utcoffset() is None for s in samples):
            return None
        if any(not 0 <= ((reference-s.sampled_at).total_seconds() if preceding else
                          (s.sampled_at-reference).total_seconds()) <= max_age_seconds for s in samples):
            return None
    first, last = stable_weight(before), stable_weight(after)
    if first is None or last is None or last > first:
        return None
    return round(first - last, 3)


@dataclass(frozen=True)
class FusedVisit:
    behavior: BehaviorRecord
    drinking: DrinkingSession | None
    estimated_food_consumed_grams: float | None


class SessionFusion:
    """Associates confirmed visits with validated evidence; never triggers feeding."""

    def __init__(self, repository: RecordRepository | None = None):
        self.repository = repository

    def fuse(self, start: SessionSignal, end: SessionSignal, *,
             feeding: FeedingSession | None = None,
             weight_before: list[WeightSample] | None = None,
             weight_after: list[WeightSample] | None = None,
             source: str = "UNVALIDATED", completion_reason: str = "BEHAVIOR_STOPPED",
             food_added_during_session: bool = False) -> FusedVisit:
        if start.signal != SignalType.START or end.signal != SignalType.END or \
                start.session_id != end.session_id or end.ended_at is None or \
                start.identity != end.identity or start.behavior != end.behavior:
            raise ValueError("mismatched temporal visit signals")
        associated = (feeding is not None and start.behavior == Behavior.EATING and
                      feeding.cat_identity == start.identity and
                      feeding.requested_at <= start.started_at <= feeding.requested_at + timedelta(hours=1))
        behavior = BehaviorRecord(session_id=start.session_id, cat_identity=start.identity,
                                  behavior=start.behavior, started_at=start.started_at,
                                  ended_at=end.ended_at, duration_seconds=end.duration_seconds,
                                  feeding_session_id=feeding.session_id if associated else None,
                                  food_type=feeding.food_type if associated else None,
                                  source=source)
        drinking = (DrinkingSession(session_id=start.session_id, cat_identity=start.identity,
                                    started_at=start.started_at, ended_at=end.ended_at,
                                    duration_seconds=end.duration_seconds, source=source)
                    if start.behavior == Behavior.DRINKING else None)
        consumed = (estimate_consumed(start, end, weight_before or [], weight_after or [])
                     if associated and not food_added_during_session else None)
        if consumed is not None and feeding.dispensed_grams is not None and consumed > feeding.dispensed_grams:
            consumed = None  # disappearance exceeding known dispensed portion is not valid consumption
        behavior = behavior.model_copy(update={"completion_reason": completion_reason,
                                                "estimated_consumed_grams": consumed,
                                                "weight_evidence_validated": consumed is not None})
        if self.repository is not None:
            self.repository.add_visit(behavior, drinking)
        return FusedVisit(behavior, drinking, consumed)
