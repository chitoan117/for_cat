"""Synthetic supplied records only; no physical sensor/AI validation."""
from datetime import datetime,timedelta,timezone,date
import pytest
from app.ai.models import Identity
from app.behavior.models import Behavior
from app.analytics.reports import FoodDefinition,FoodTrial,preference_report,activity_report,drinking_report
from app.storage.records import FeedingSession,DrinkingSession,BehaviorRecord
from app.vision.tracking import TrackLedger,TrackEvidence,attribution


@pytest.mark.parametrize("identities,eligible",[
    ([Identity.OWNER_CAT],True),([Identity.OTHER_CAT],False),
    ([Identity.OWNER_CAT,Identity.OTHER_CAT],False),([Identity.OTHER_CAT,Identity.OTHER_CAT],False),
    ([Identity.UNKNOWN],False),([],False)])
def test_multicat_attribution_conservative(identities,eligible):
    evidence=[TrackEvidence(str(i),identity,Behavior.EATING) for i,identity in enumerate(identities)]
    result=attribution(evidence)
    assert result["preference_eligible"]==eligible and not result["automatic_feed_authorized"]
    if len(identities)!=1: assert result["subject_track"]=="AMBIGUOUS"


def test_tracks_reuse_id_expire_and_bound_state():
    ledger=TrackLedger(ttl_seconds=2,max_tracks=2)
    t=TrackEvidence("subject",Identity.OWNER_CAT,Behavior.EATING)
    assert ledger.update([t],0)[0]["first_seen"]==0
    assert ledger.update([t],1)[0]["first_seen"]==0
    assert ledger.update([],4)==[]
    assert ledger.update([t],5)[0]["first_seen"]==5
    with pytest.raises(ValueError): ledger.update([t,t],6)
    with pytest.raises(ValueError): ledger.update([],3)
    assert attribution([TrackEvidence("cat",Identity.OWNER_CAT,Behavior.EATING,True)])["subject_track"]=="AMBIGUOUS"


def test_food_report_excludes_ambiguous_and_unvalidated_no_hunger_inference():
    now=datetime(2026,10,3,tzinfo=timezone.utc); food=FoodDefinition(food_id="food_a",display_name="Food A")
    s=FeedingSession(session_id="synthetic",requested_at=now,cat_identity=Identity.OWNER_CAT,food_type="food_a",
        source="SYNTHETIC_TEST_DATA",dispensed_grams=20,estimated_consumed_grams=10,approach_delay_seconds=5,repeat_visits=1)
    trial=FoodTrial(feeding=s,subject_track="cat",attribution="CLEAN",bowl_position="left")
    result=preference_report(food,[trial])
    assert result["report"]=="BEHAVIORAL PREFERENCE TREND" and result["valid_sessions"]==0
    assert result["confidence"] is None and not result["hunger_inferred"]
    # Caller-declared validation tests the filter, not actual sensor validation.
    trial=trial.model_copy(update={"feeding":s.model_copy(update={"source":"VALIDATED_SENSOR"}),"attribution":"AMBIGUOUS"})
    assert preference_report(food,[trial])["valid_sessions"]==0
    clean=trial.model_copy(update={"attribution":"CLEAN"})
    result=preference_report(food,[clean,clean])
    assert result["valid_sessions"]==1 and result["insufficient_data_reasons"]["DUPLICATE_SESSION"]==1


def test_daily_activity_unknowns_downtime_and_drinking_never_volume():
    now=datetime(2026,10,3,tzinfo=timezone.utc)
    drink=DrinkingSession(session_id="d",started_at=now,ended_at=now+timedelta(seconds=5),duration_seconds=5,source="SYNTHETIC_TEST_DATA")
    eating=BehaviorRecord(session_id="e",behavior=Behavior.EATING,started_at=now,cat_identity=Identity.UNKNOWN)
    report=activity_report(now.date(),eating=[eating],drinking=[drink],recognition=[{"date":"2026-10-03","identity":"UNKNOWN","ambiguous":True}])
    assert report["drinking"]["drinking_event_count"]==1 and report["drinking"]["water_volume"] is None
    assert report["food_consumed_grams"] is None and report["system_downtime_seconds"] is None
    assert report["unknown_ambiguous_events"]==2 and report["health_diagnosis"] is None
    with pytest.raises(ValueError): activity_report(now.date(),downtime_seconds=-1)
