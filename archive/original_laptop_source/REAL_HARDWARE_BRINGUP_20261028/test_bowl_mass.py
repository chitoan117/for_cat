from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import pytest

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
from app.bowl_mass import BowlMassTracker,Context,GrossSample
from app.hx711_view import Hx711GramView
from bowl_log import MASSES,raw_stats,fit_candidate,analyze,save_new,sha

CTX=Context('CURRENT_TEST','INOX_NEW','NEW_PAIR','BOOT_A',calibration_current_mount=True)
def window(gross,now,ctx=CTX):return [GrossSample(gross,now-900+i*300,ctx) for i in range(4)]
def tracker():
    m=BowlMassTracker(CTX);m.confirm_empty_bowl(window(95,1900),1900,owner_confirmed_empty=True);return m
def dispensed():
    m=tracker();m.begin_dispense(window(95,2900),2900);return m,m.finish_dispense(window(130,4900),4900)

def test_bowl95_plus_food35_is_gross130_not35():
    m,result=dispensed();assert result['actual_dispensed']==35 and result['gross_measurement']==130 and result['empty_bowl_gross']==95
    assert result['actuation_authorized'] is False and result['physical_validated'] is False
    assert m.gross_after_dispense-m.gross_before_dispense==35

@pytest.mark.parametrize('amount',[5,10,20,35,38])
def test_reference_deltas_have_no_bowl_double_subtraction(amount):
    result=tracker().reference_delta(window(95+amount,3900),3900)
    assert result['food_delta']==amount and result['gross_measurement']==95+amount

@pytest.mark.parametrize('final,consumed,label',[(100,30,'LIKE'),(125,5,'DISLIKE'),(112,18,'LIKE'),(113,17,'UNCERTAIN')])
def test_gross_consumption_food_A_B_boundaries(final,consumed,label):
    m,_=dispensed();m.begin_meal('FOOD_A' if consumed>=18 else 'FOOD_B',window(130,6900),6900)
    for now in range(7200,66901,300):m.observe_meal(GrossSample(130 if now<26900 else final,now,CTX),now)
    result=m.finish_meal(window(final,66900),66900,measurement_source='SIMULATED_REFERENCE_WEIGHTS')
    assert result['consumed']==consumed and result['classification']==label
    assert result['remaining_food_mass']==final-95 and result['meal_start_gross']==130 and result['meal_end_gross']==final
    assert result['actuation_authorized'] is False and 'NOT_PROOF' in result['inference']

def test_leftover_food_never_accepted_as_empty():
    m=tracker()
    with pytest.raises(ValueError,match='BOWL_NOT_EMPTY'):m.begin_dispense(window(100,3900),3900)
    assert m.phase=='BLOCKED' and m.empty_bowl_gross is None

@pytest.mark.parametrize('change',[{'mount_id':'MOVED'},{'calibration_id':'OTHER'},{'boot_id':'REBOOTED'},{'tare_generation':1}])
def test_old_context_tare_reboot_bowl_mount_never_reuses_baseline(change):
    m=tracker();other=replace(CTX,**change)
    with pytest.raises(ValueError,match='CHANGED'):m.begin_dispense(window(95,3900,other),3900)
    assert m.empty_bowl_gross is None

def test_old_calibration_and_unconfirmed_empty_are_blocked():
    with pytest.raises(ValueError,match='CURRENT_MOUNT'):BowlMassTracker(replace(CTX,calibration_current_mount=False))
    m=BowlMassTracker(CTX)
    with pytest.raises(ValueError,match='OWNER_EMPTY'):m.confirm_empty_bowl(window(95,1900),1900)
    m.confirm_empty_bowl(window(95,1900),1900,owner_confirmed_empty=True)
    with pytest.raises(ValueError,match='NEW_SESSION'):m.confirm_empty_bowl(window(95,3900),3900,owner_confirmed_empty=True)

@pytest.mark.parametrize('gross',[None,float('nan'),float('inf'),1001])
def test_invalid_measurements_are_not_zero(gross):
    m=tracker()
    with pytest.raises(ValueError,match='INVALID'):m.reference_delta(window(gross,3900),3900)
    assert m.empty_bowl_gross is None

def test_creep_unstable_and_stale_block():
    for samples,now in [([GrossSample(95+i*.2,1000+i*300,CTX) for i in range(4)],1900), (window(95,1900),5000)]:
        m=tracker()
        with pytest.raises(ValueError):m.reference_delta(samples,now)
        assert m.phase=='BLOCKED'

def test_overshoot_timeout_and_no_rebase_when_active():
    m=tracker();m.begin_dispense(window(95,2900),2900)
    with pytest.raises(ValueError,match='NEW_SESSION'):m.confirm_empty_bowl(window(95,3900),3900,owner_confirmed_empty=True)
    with pytest.raises(ValueError,match='OVERSHOOT'):m.finish_dispense(window(131,4900),4900)
    m=tracker();m.begin_dispense(window(95,2900),2900)
    with pytest.raises(ValueError,match='TIMEOUT'):m.finish_dispense(window(120,22900),22900)

def test_empty_return_drift_and_bowl_movement_invalidates():
    m=tracker()
    with pytest.raises(ValueError,match='BOWL_MOVED'):m.check_empty_return(window(94,3900),3900)
    assert m.empty_bowl_gross is None
    m,_=dispensed();m.begin_meal('A',window(130,6900),6900)
    with pytest.raises(ValueError,match='BOWL_MOVED'):m.observe_meal(GrossSample(90,7200,CTX),7200)

def test_meal_requires_continuous_data_no_refill_or_tare():
    m,_=dispensed();m.begin_meal('A',window(130,6900),6900)
    with pytest.raises(ValueError,match='CONTINUITY'):m.finish_meal(window(100,66900),66900)
    m,_=dispensed();m.begin_meal('A',window(130,6900),6900)
    m.observe_meal(GrossSample(120,7200,CTX),7200)
    with pytest.raises(ValueError,match='REFILL'):m.observe_meal(GrossSample(125,7500,CTX),7500)

def synthetic_capture(folder,session,index,phase,ref,boot=1,shift=0):
    path=folder/('capture_%04d'%index);path.mkdir()
    raw=-670000-ref*1000+shift
    samples=[{'monotonic_ms':1000+i*300,'median_raw':raw,'valid':True,'measurement_grams':ref-shift/1000,'display_grams':ref} for i in range(110)]
    (path/'serial_raw.bin').write_bytes(b'SYNTHETIC_ONLY_NOT_REAL_UART_'+str(index).encode())
    body={'kind':'SYNTHETIC_TEST_ONLY','mount_id':session['mount_id'],'session_id':session['session_id'],
          'phase':phase,'reference_g':ref,'boot_nonce':boot,'samples':samples,'raw_sha256':sha(path/'serial_raw.bin'),
          'full_status':[{'mount_binding_match':True,'calibration_source':'ESP32_NVS_CURRENT_MOUNT_PENDING',
                          'offset':-670000,'scale_factor_counts_per_gram':-1000}]}
    save_new(path/'capture.json',body)

def test_fresh_fit_frozen_verify_and_reboot_no_false_physical_pass(tmp_path):
    session={'kind':'INOX_BOWL_CURRENT_MOUNT_VALIDATION','mount_id':'SYNTHETIC_INOX','session_id':'SYNTHETIC_ONLY'}
    for i,m in enumerate(MASSES):synthetic_capture(tmp_path,session,i,'FIT',m)
    model=fit_candidate(tmp_path,session)
    assert model['counts_per_gram']==-1000 and model['physical_pass'] is False and model['validation_passed'] is False
    with pytest.raises(ValueError,match='frozen'):fit_candidate(tmp_path,session)
    index=10;synthetic_capture(tmp_path,session,index,'VERIFY',0)
    for m in MASSES[1:]:
        index+=1;synthetic_capture(tmp_path,session,index,'VERIFY',m)
        index+=1;synthetic_capture(tmp_path,session,index,'RETURN',0)
    for phase,mass in [('REBOOT_EMPTY',0),('REBOOT_VERIFY',35),('REBOOT_RETURN',0)]:
        index+=1;synthetic_capture(tmp_path,session,index,phase,mass,boot=2)
    result=analyze(tmp_path,session)
    assert result['verification_sequence_complete'] and result['nvs_same_pair_after_reboot']
    assert result['assessment']=='POINTS_WITHIN_CRITERIA_PENDING_OWNER_EVIDENCE_REVIEW' and result['physical_pass'] is False
    assert result['points'][0]['measurement_grams_unfiltered']['count']==110

def test_raw_stats_detects_restarts_and_invalid_not_zero():
    with pytest.raises(ValueError):raw_stats([{'monotonic_ms':1000,'median_raw':-500000},{'monotonic_ms':100,'median_raw':-500000}])
    with pytest.raises(ValueError):raw_stats([{'monotonic_ms':1000,'median_raw':0},{'monotonic_ms':1300,'median_raw':0}])

def test_current_mount_runtime_mask_does_not_reuse_old_host_calibration(tmp_path):
    view=Hx711GramView(tmp_path/'unused.db',clock=lambda:1,current_mount_id='INOX_NEW')
    class Store:
        def active(self):return {'calibration_state':'OLD_VALIDATED_MODEL','calibration_id':'OLD_PAIR'}
    view.store=Store();state={'weight':{}}
    view.apply(state,{})
    assert state['weight']['calibration_state']=='MOUNT_BINDING_MISMATCH' and state['weight']['grams'] is None
    assert state['weight']['controller_calibration_state']=='UNCHANGED_NOT_AUTHORIZED_FOR_ACTUATION'
