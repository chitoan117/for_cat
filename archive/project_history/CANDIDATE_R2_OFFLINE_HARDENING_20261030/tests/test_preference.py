import sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'candidate/backend'))
from app.analytics.preference import trend,PreferencePolicy
from app.storage.records import FeedingSession,DrinkingSession,BehaviorRecord
from app.storage.repositories import RecordRepository
from app.ai.models import Identity
def row(n,consumed=30):
    start=datetime(2026,10,30,tzinfo=timezone.utc)+timedelta(minutes=n*2)
    return FeedingSession(session_id='SYNTHETIC_'+str(n),cat_identity=Identity.OWNER_CAT,source='SYNTHETIC_TEST_DATA',
        requested_at=start,food_type='FOOD',result='SUCCESS',dispensed_grams=35,estimated_consumed_grams=consumed,
        weight_before_eating=35,weight_after_eating=35-consumed,weight_evidence_validated=True,
        approach_delay_seconds=10,repeat_visits=1,eating_started_at=start,eating_finished_at=start+timedelta(seconds=60))
P=PreferencePolicy(allow_synthetic_test_data=True)
def test_three_independent_sessions_required_and_no_duplicate_inflation():
    assert trend('FOOD',[row(0)],P)['status']=='INSUFFICIENT_DATA'
    assert trend('FOOD',[row(0)]*4,P)['sessions']==1
    result=trend('FOOD',[row(0),row(1),row(2)],P);assert result['status']=='SUFFICIENT_DATA' and result['preference_trend']=='HIGH'
@pytest.mark.parametrize('fault',['ERROR','short','missing_weight','wrong_weight','public_identity','other_identity','unvalidated_weight','overlap','conflict'])
def test_unreliable_evidence_cannot_make_preference(fault):
    rows=[row(n) for n in range(3)]
    if fault=='ERROR':rows=[x.model_copy(update={'result':'ERROR'}) for x in rows]
    if fault=='short':rows=[x.model_copy(update={'eating_finished_at':x.eating_started_at+timedelta(seconds=1)}) for x in rows]
    if fault=='missing_weight':rows=[x.model_copy(update={'weight_before_eating':None}) for x in rows]
    if fault=='wrong_weight':rows=[x.model_copy(update={'weight_after_eating':34}) for x in rows]
    if fault=='public_identity':rows=[x.model_copy(update={'source':'VALIDATED_SENSOR','identity_verified':True,'identity_source':'PUBLIC_CAT_DATASET','identity_model_id':'PUBLIC','owner_enrollment_id':None}) for x in rows]
    if fault=='other_identity':rows=[x.model_copy(update={'cat_identity':Identity.OTHER_CAT}) for x in rows]
    if fault=='unvalidated_weight':rows=[x.model_copy(update={'weight_evidence_validated':False}) for x in rows]
    if fault=='overlap':rows=[x.model_copy(update={'eating_started_at':rows[0].eating_started_at,'eating_finished_at':rows[0].eating_finished_at}) for x in rows]
    if fault=='conflict':rows.append(rows[0].model_copy(update={'estimated_consumed_grams':20,'weight_after_eating':15}))
    assert trend('FOOD',rows,P)['status']=='INSUFFICIENT_DATA'
def test_public_or_mock_data_not_used_by_default():
    assert trend('FOOD',[row(n) for n in range(3)])['status']=='INSUFFICIENT_DATA'
    rows=[row(n).model_copy(update={'source':'VALIDATED_SENSOR'}) for n in range(3)]
    assert trend('FOOD',rows)['status']=='INSUFFICIENT_DATA'
def test_reliable_consumed_amount_changes_thresholds_without_training_claim():
    high=trend('FOOD',[row(n,35) for n in range(3)],P)
    low=trend('FOOD',[row(n,0).model_copy(update={'approach_delay_seconds':120,'repeat_visits':0}) for n in range(3)],P)
    assert high['preference_trend']=='HIGH' and low['preference_trend']=='LOW' and high['method']=='EXPERIMENTAL'
