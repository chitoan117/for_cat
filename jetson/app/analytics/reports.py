"""Read-only supplied-evidence reports. No diagnosis, hunger inference or water volume."""
from collections import Counter
from datetime import date
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ai.models import Identity
from app.analytics.preference import PreferencePolicy, trend
from app.storage.records import FeedingSession, DrinkingSession


class FoodDefinition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    food_id: str=Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    display_name: str=Field(min_length=1,max_length=128)
    batch_variant: str | None=Field(default=None,max_length=128)
    notes: str | None=Field(default=None,max_length=512)


class FoodTrial(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    feeding: FeedingSession
    subject_track: str=Field(default="AMBIGUOUS",min_length=1,max_length=64)
    time_since_last_feed_seconds: float | None=Field(default=None,ge=0)
    portion_size_grams: float | None=Field(default=None,ge=0)
    time_of_day: str | None=Field(default=None,max_length=64)
    food_freshness: str | None=Field(default=None,max_length=128)
    bowl_position: str | None=Field(default=None,max_length=128)
    environmental_disturbance: str | None=Field(default=None,max_length=256)
    attribution: Literal["CLEAN","AMBIGUOUS"]="AMBIGUOUS"


def preference_report(food: FoodDefinition, trials: list[FoodTrial], *, min_sessions=3):
    if len(trials)>10000:
        raise ValueError("report budget exceeded")
    selected=[]; reasons=Counter(); seen=set()
    for trial in trials:
        session=trial.feeding
        if session.food_type!=food.food_id: continue
        if session.session_id in seen: reasons["DUPLICATE_SESSION"]+=1; continue
        seen.add(session.session_id)
        if trial.attribution!="CLEAN" or trial.subject_track=="AMBIGUOUS" or session.cat_identity!=Identity.OWNER_CAT:
            reasons["AMBIGUOUS_OR_NON_OWNER"]+=1; continue
        if session.source!="VALIDATED_SENSOR": reasons["WEIGHT_NOT_VALIDATED"]+=1; continue
        if session.dispensed_grams is None or session.dispensed_grams<=0 or session.estimated_consumed_grams is None or session.estimated_consumed_grams>session.dispensed_grams or session.approach_delay_seconds is None or session.repeat_visits is None:
            reasons["INCOMPLETE_MEASUREMENTS"]+=1; continue
        selected.append(session)
        if any(getattr(trial, name) is None for name in ("time_since_last_feed_seconds", "time_of_day",
                "food_freshness", "bowl_position", "environmental_disturbance")):
            reasons["MISSING_CONFOUNDERS"] += 1
    result=trend(food.food_id,selected,PreferencePolicy(min_sessions=min_sessions))
    if reasons["MISSING_CONFOUNDERS"]:
        result.update(status="INSUFFICIENT_DATA", preference_trend=None, evidence={})
    if result["status"]=="INSUFFICIENT_DATA": reasons["INSUFFICIENT_VALID_SESSIONS"]+=1
    ratios=[s.estimated_consumed_grams/s.dispensed_grams for s in selected]
    return {"report":"BEHAVIORAL PREFERENCE TREND","food":food.model_dump(),"analysis":result,
        "valid_sessions":len(selected),"sample_count":len(selected),"confidence":None,
        "consumption_ratio":mean(ratios) if ratios else None,
        "approach_latency_seconds":[s.approach_delay_seconds for s in selected],
        "eating_duration_seconds":[(s.eating_finished_at-s.eating_started_at).total_seconds() for s in selected if s.eating_started_at and s.eating_finished_at],
        "leftover_grams":[s.dispensed_grams-s.estimated_consumed_grams for s in selected],
        "repeat_visits":[s.repeat_visits for s in selected],"insufficient_data_reasons":dict(reasons),
        "confounders":[t.model_dump(mode="json",exclude={"feeding"}) for t in trials if t.feeding.food_type==food.food_id],
        "hunger_inferred":False,"evidence":"CALLER_SUPPLIED; provenance must be independently reviewed"}


def drinking_report(sessions: list[DrinkingSession], day: date):
    if len(sessions)>10000: raise ValueError("report budget exceeded")
    unique={s.session_id:s for s in sessions if s.started_at.date()==day}
    return {"date":day.isoformat(),"drinking_event_count":len(unique),"daily_frequency":len(unique),
        "start_times":[s.started_at.isoformat() for s in sorted(unique.values(),key=lambda x:x.started_at)],
        "duration_seconds":[s.duration_seconds for s in unique.values()],"water_volume":None,
        "source_counts":dict(Counter(s.source for s in unique.values())),"health_diagnosis":None}


def activity_report(day: date, *, eating=None, drinking=None, feeding=None, recognition=None, downtime_seconds=None):
    eating,drinking,feeding,recognition=eating or [],drinking or [],feeding or [],recognition or []
    if any(len(items)>10000 for items in (eating,drinking,feeding,recognition)): raise ValueError("report budget exceeded")
    if downtime_seconds is not None and not 0<=downtime_seconds<=86400: raise ValueError("invalid measured downtime")
    eats=[s for s in eating if s.started_at.date()==day]
    feeds={s.session_id:s for s in feeding if s.requested_at.date()==day}
    labels=Counter(r["identity"] for r in recognition if r["date"]==day.isoformat())
    # Avoid counting the same feeding estimate and weight-backed eating visit twice.
    associated={s.feeding_session_id for s in eats if s.weight_evidence_validated and s.feeding_session_id}
    amounts=[s.estimated_consumed_grams for s in eats if s.source=="VALIDATED_SENSOR" and s.weight_evidence_validated and s.estimated_consumed_grams is not None]
    amounts.extend(s.estimated_consumed_grams for s in feeds.values() if s.source=="VALIDATED_SENSOR" and s.session_id not in associated and s.estimated_consumed_grams is not None)
    return {"date":day.isoformat(),"eating_sessions":len({s.session_id for s in eats}),"drinking":drinking_report(drinking,day),
        "food_consumed_grams":sum(amounts) if amounts else None,"feeding_requests":len(feeds),
        "feeding_results":dict(Counter(s.result for s in feeds.values())),"recognition_summary":dict(labels),
        "unknown_ambiguous_events":sum(s.cat_identity==Identity.UNKNOWN for s in eats)+sum(r.get("ambiguous",False) for r in recognition if r["date"]==day.isoformat()),
        "system_downtime_seconds":downtime_seconds,"health_diagnosis":None,
        "evidence":"SUPPLIED_RECORDS_ONLY; no automatic physical validation"}
