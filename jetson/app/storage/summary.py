"""Read-only UTC daily summaries; missing measurements stay unknown."""

from datetime import date

from app.analytics.preference import PreferencePolicy, trend
from app.behavior.models import Behavior
from app.storage.repositories import RecordRepository


def daily_summary(repo: RecordRepository, day: date, min_sessions: int = 3) -> dict:
    feeds = repo.list("feeding", limit=1000, day=day)
    drinks = repo.list("drinking", limit=1000, day=day)
    eating_visits = [x for x in repo.list("behavior", limit=1000, day=day)
                     if x.behavior == Behavior.EATING]
    associated_ids = {x.feeding_session_id for x in eating_visits
                      if x.weight_evidence_validated and x.feeding_session_id}
    # Never double-count a typed feeding estimate and its visit projection.
    consumed = [x.estimated_consumed_grams for x in feeds
                if x.estimated_consumed_grams is not None and x.source == "VALIDATED_SENSOR"
                and x.session_id not in associated_ids]
    consumed.extend(x.estimated_consumed_grams for x in eating_visits
                    if x.weight_evidence_validated and x.source == "VALIDATED_SENSOR"
                    and x.estimated_consumed_grams is not None)
    feed_truncated = repo.count("feeding", day) > len(feeds)
    drink_truncated = repo.count("drinking", day) > len(drinks)
    preferences = [x for x in repo.list("preference", limit=1000)
                   if x.status == "SUFFICIENT_DATA" and x.trend is not None]
    rank = {"HIGH": 3, "MODERATE": 2, "LOW": 1}
    strongest = max(preferences, key=lambda x: (rank[x.trend], x.sessions), default=None)
    eating_durations = [x.duration_seconds for x in eating_visits if x.duration_seconds is not None]
    if not eating_durations:
        eating_durations = [(x.eating_finished_at - x.eating_started_at).total_seconds()
                            for x in feeds if x.eating_started_at and x.eating_finished_at]
    all_feeds = repo.list("feeding", limit=1000)
    computed = [trend(food_type, all_feeds, PreferencePolicy(min_sessions=min_sessions))
                for food_type in sorted({x.food_type for x in all_feeds if x.food_type})]
    if repo.count("feeding") > len(all_feeds):
        computed = []  # never rank a truncated sample as a complete trend
    sufficient = [x for x in computed if x["status"] == "SUFFICIENT_DATA"]
    best = max(sufficient, key=lambda x: (x["evidence"]["experimental_score"], x["sessions"]), default=None)
    return {
        "date": day.isoformat(),
        "feeding_sessions": None if feed_truncated else sum(x.result == "SUCCESS" for x in feeds),
        "feeding_requests": repo.count_feed_requests(day),
        "drinking_sessions": repo.count("drinking", day),
        "session_details_truncated": feed_truncated or drink_truncated or repo.count("behavior", day) > 1000,
        "eating_times": sorted({x.eating_started_at.isoformat() for x in feeds if x.eating_started_at}
                               | {x.started_at.isoformat() for x in eating_visits}),
        "eating_visits": [{"identity": x.cat_identity.value,
                            "started_at": x.started_at.isoformat(),
                            "duration_seconds": x.duration_seconds} for x in eating_visits],
        "drinking_times": [x.started_at.isoformat() for x in drinks],
        "eating_duration_seconds": eating_durations,
        "drinking_duration_seconds": [x.duration_seconds for x in drinks if x.duration_seconds is not None],
        "reliable_food_consumed_grams": round(sum(consumed), 3) if consumed and not feed_truncated else None,
        "strongest_observed_preference_trend": best["food_type"] if best else strongest.food_type if strongest else None,
        "preference_status": "EXPERIMENTAL" if best or strongest else "INSUFFICIENT_DATA",
    }
