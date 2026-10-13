"""Experimental multi-session behavioral preference trends, not animal emotion."""

from dataclasses import dataclass
from math import isfinite
from statistics import mean, pstdev

from app.storage.records import FeedingSession
from app.ai.models import Identity


@dataclass(frozen=True)
class PreferencePolicy:
    min_sessions: int = 3
    consumption_weight: float = 0.55
    approach_weight: float = 0.25
    repeat_weight: float = 0.20
    approach_reference_seconds: float = 120
    high_threshold: float = 0.70
    low_threshold: float = 0.35
    allow_synthetic_test_data: bool = False

    def __post_init__(self):
        if self.min_sessions < 2 or any(not isfinite(x) or x < 0 for x in (
            self.consumption_weight, self.approach_weight, self.repeat_weight,
        )) or abs(sum((self.consumption_weight, self.approach_weight,
                      self.repeat_weight)) - 1) > 1e-6:
            raise ValueError("invalid preference weights/minimum")
        if any(not isfinite(x) for x in (self.approach_reference_seconds, self.low_threshold,
                                          self.high_threshold)) or self.approach_reference_seconds <= 0 or \
                not 0 <= self.low_threshold < self.high_threshold <= 1:
            raise ValueError("invalid preference thresholds")


_DEFAULT_POLICY = PreferencePolicy()  # frozen/immutable, deliberately shared


def trend(food_type: str, sessions: list[FeedingSession], policy: PreferencePolicy = _DEFAULT_POLICY) -> dict:
    valid = [s for s in sessions if s.food_type == food_type and
             s.cat_identity == Identity.OWNER_CAT and
             (s.source == "VALIDATED_SENSOR" or
              policy.allow_synthetic_test_data and s.source == "SYNTHETIC_TEST_DATA")
             and s.dispensed_grams is not None and s.dispensed_grams > 0
             and s.estimated_consumed_grams is not None
             and 0 <= s.estimated_consumed_grams <= s.dispensed_grams
             and all(isfinite(x) for x in (s.dispensed_grams, s.estimated_consumed_grams,
                                            s.approach_delay_seconds or 0))
             and s.approach_delay_seconds is not None and s.repeat_visits is not None]
    valid_ids = {s.session_id for s in valid}
    evidence = {"food_type": food_type, "sessions": len(valid_ids),
                "session_ids": sorted(valid_ids), "status": "INSUFFICIENT_DATA",
                "preference_trend": None, "method": "EXPERIMENTAL", "evidence": {}}
    if len(valid_ids) < policy.min_sessions:
        return evidence
    # One row per session; duplicate IDs cannot inflate evidence.
    unique = {s.session_id: s for s in valid}
    ratios = [s.estimated_consumed_grams / s.dispensed_grams for s in unique.values()]
    delays = [s.approach_delay_seconds for s in unique.values()]
    repeats = [min(s.repeat_visits, 1) for s in unique.values()]
    consumption = mean(ratios)
    approach = mean(max(0.0, 1 - d / policy.approach_reference_seconds) for d in delays)
    repeat_rate = mean(repeats)
    eating_durations = [(s.eating_finished_at - s.eating_started_at).total_seconds()
                        for s in unique.values() if s.eating_started_at and s.eating_finished_at]
    score = (policy.consumption_weight * consumption + policy.approach_weight * approach
             + policy.repeat_weight * repeat_rate)
    evidence["status"] = "SUFFICIENT_DATA"
    evidence["preference_trend"] = ("HIGH" if score >= policy.high_threshold else
                                    "LOW" if score < policy.low_threshold else "MODERATE")
    evidence["evidence"] = {
        "consumption_ratio_mean": round(consumption, 4),
        "consumption_ratio_stddev": round(pstdev(ratios), 4),
        "approach_delay_mean_seconds": round(mean(delays), 3),
        "repeat_visit_rate": round(repeat_rate, 4),
        "eating_duration_mean_seconds": round(mean(eating_durations), 3) if eating_durations else None,
        "leftover_mean_grams": round(mean(s.dispensed_grams - s.estimated_consumed_grams
                                            for s in unique.values()), 3),
        "experimental_score": round(score, 4),
    }
    return evidence
