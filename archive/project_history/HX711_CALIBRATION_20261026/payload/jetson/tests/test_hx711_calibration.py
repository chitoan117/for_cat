"""Synthetic-reference SOFTWARE tests only. Not physical calibration evidence."""
import copy
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.hx711_calibration import CalibrationStore, CRITERIA, MASSES, binding, raw_statistics, checksum, safe_bridge
from app.hx711_view import Hx711GramView
from app.meal_plans import MealPlans, CreatePlan


def flags():
    return {**{k:False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution')},'actuator_outputs_enabled':0}


def bridge(raw=-600000,ms=1000,host='host_a'):
    return {'usb_vid':'1a86','usb_pid':'55d3','usb_serial':'5C85066678','host_boot_id':host,
      'last_rx_monotonic_ms':100000,'last_received_at':'synthetic-time','telemetry_usable_now':True,
      'health':'ESP32_CONNECTED','unsafe_telemetry_latched':False,
      'telemetry':{'mode':'diag_current_hardware','monotonic_ms':ms,'safety':flags(),
        'sensors':{'hx711':{'raw_counts':raw,'raw_available':True,'firmware_calibrated':False}}}}


def context(host='host_a',boot=100000):
    return {'binding':binding(bridge()),'host_boot_id':host,'boot_estimate_ms':boot,
            'capture_origin':'SYNTHETIC_UNIT_TEST_NOT_HARDWARE','safety_before':flags(),'safety_after':flags()}


def samples(mass,slope=1000,offset=-600000):
    return [{'raw':offset+mass*slope+[-1,0,1][i%3],'device_ms':1000+i*1000} for i in range(31)]


def fitted(tmp_path,slope=1000):
    store=CalibrationStore(tmp_path/'state.db');session=store.new(context()['binding'],tmp_path/'evidence')
    for mass in MASSES:store.record(session['session_id'],'fit',mass,samples(mass,slope),context())
    store.fit(session['session_id']);return store,session['session_id']


def activated(tmp_path,slope=1000):
    store,identifier=fitted(tmp_path,slope)
    for mass in (*MASSES,0):store.record(identifier,'verify',mass,samples(mass,slope),context())
    store.activate(identifier,context());return store,identifier


@pytest.mark.parametrize('slope',[1000,-1000])
def test_multisample_multipoint_fit_signed_factor_and_independent_validation(tmp_path,slope):
    store,identifier=fitted(tmp_path,slope);candidate=store.session(identifier)['candidate']
    assert candidate['grams_per_count']==pytest.approx(1/slope)
    assert candidate['tare_offset_counts']==pytest.approx(-600000-1/31)
    assert store.active() is None  # fit is not yet calibration authority
    with pytest.raises(ValueError):store.activate(identifier,context())
    for mass in (*MASSES,0):store.record(identifier,'verify',mass,samples(mass,slope),context())
    model=store.activate(identifier,context())
    assert model['validation_passed'] is True
    assert model['calibration_state']=='CALIBRATED_PENDING_PERSISTENCE'
    assert CalibrationStore(store.path).active()==model
    assert store.session(identifier)['physical_result']=='PHYSICAL_CALIBRATION_IN_PROGRESS'


def test_no_single_sample_or_replayed_report_is_a_calibration_window(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');session=store.new(context()['binding'],tmp_path)
    for values in ([{'raw':1,'device_ms':1}], samples(0)[:10], [{'raw':1,'device_ms':1}]*31):
        with pytest.raises(ValueError):store.record(session['session_id'],'fit',0,values,context())
    assert store.points(session['session_id'])==[] and store.active() is None


def test_only_isolated_small_fraction_of_outliers_may_be_removed():
    raw=samples(0);raw[10]['raw']+=10000
    result=raw_statistics(raw);assert result['rejected_indices']==[10] and result['inlier_count']==30
    raw[11]['raw']+=10000
    with pytest.raises(ValueError,match='contiguous'):raw_statistics(raw)
    raw=samples(0)
    for i in (2,7,12,17):raw[i]['raw']+=10000
    with pytest.raises(ValueError,match='too many'):raw_statistics(raw)


@pytest.mark.parametrize('bad',[-8388608,8388607,float('nan'),float('inf'),True,1.5])
def test_rail_nonfinite_boolean_fractional_raw_rejected(bad):
    raw=samples(0);raw[1]['raw']=bad
    with pytest.raises(ValueError):raw_statistics(raw)


def test_noise_and_drift_are_not_hidden_by_robust_fit(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');s=store.new(context()['binding'],tmp_path)
    for mass in MASSES:
        values=samples(mass)
        if mass==20:
            for i,p in enumerate(values):p['raw']+=i*30
        store.record(s['session_id'],'fit',mass,values,context())
    with pytest.raises(ValueError):store.fit(s['session_id'])
    assert store.active() is None


def test_nonmonotonic_response_and_unresolvable_small_mass_fail(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');s=store.new(context()['binding'],tmp_path)
    for mass in MASSES:store.record(s['session_id'],'fit',mass,samples(mass,slope=1),context())
    with pytest.raises(ValueError,match='quantization'):store.fit(s['session_id'])
    for mass in MASSES:store.record(s['session_id'],'fit',mass,samples(10 if mass==20 else mass),context())
    with pytest.raises(ValueError,match='monotonic'):store.fit(s['session_id'])


def test_fit_needs_all_references_and_consistent_boot(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');s=store.new(context()['binding'],tmp_path)
    store.record(s['session_id'],'fit',0,samples(0),context())
    with pytest.raises(ValueError,match='separate'):store.fit(s['session_id'])
    for mass in MASSES[1:]:store.record(s['session_id'],'fit',mass,samples(mass),context(host='new_boot'))
    with pytest.raises(ValueError,match='restart'):store.fit(s['session_id'])


def test_validation_is_independent_and_requires_return_to_zero(tmp_path):
    store,identifier=fitted(tmp_path)
    with pytest.raises(ValueError):store.verify(identifier)
    for mass in MASSES:store.record(identifier,'verify',mass,samples(mass),context())
    with pytest.raises(ValueError,match='return-to-zero'):store.activate(identifier,context())
    store.record(identifier,'verify',0,samples(1),context())  # bad zero must not pass
    with pytest.raises(ValueError,match='failed'):store.activate(identifier,context())
    assert store.active() is None


def test_no_persistence_pass_without_observed_restart_and_operator_confirm(tmp_path):
    store,identifier=activated(tmp_path)
    for mass in (0,35,0):store.record(identifier,'persistence',mass,samples(mass),context())
    with pytest.raises(ValueError,match='restart'):store.finish(identifier,True)
    with pytest.raises(ValueError,match='operator'):store.finish(identifier)


def test_after_restart_zero_35_zero_proves_persistence_in_isolated_fixture(tmp_path):
    store,identifier=activated(tmp_path);model=store.active();reopened=CalibrationStore(store.path)
    for mass in (0,35,0):reopened.record(identifier,'persistence',mass,samples(mass),context(host='host_after_restart'))
    result=reopened.finish(identifier,True)
    assert result['state']=='PHYSICAL_PASS'  # synthetic state-machine test ONLY
    assert reopened.active()['tare_offset_counts']==model['tare_offset_counts']
    assert reopened.active()['grams_per_count']==model['grams_per_count']


def test_other_meal_plan_config_updates_do_not_erase_calibration(tmp_path):
    store,identifier=activated(tmp_path);before=store.active()
    plans=MealPlans(store.path)
    p=plans.create(CreatePlan(plan_id='unrelated',name='config fixture',local_time='07:00',weekdays=[0]))
    plans.delete(p['plan_id'],1)
    assert CalibrationStore(store.path).active()==before
    store.new(context()['binding'],tmp_path/'new_session')
    assert store.active() is None  # explicit new tare/calibration does invalidate old authority


def test_raw_and_active_checksums_fail_closed(tmp_path):
    store,identifier=activated(tmp_path)
    with closing(sqlite3.connect(store.path)) as db:
        db.execute("UPDATE hx711_calibration_active SET body='{}'");db.commit()
    with pytest.raises(ValueError):store.active()
    with closing(sqlite3.connect(store.path)) as db:
        db.execute("UPDATE hx711_calibration_points SET body='{}'");db.commit()
    with pytest.raises(ValueError):store.points(identifier)


def test_unsafe_state_and_wrong_device_never_capture(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');s=store.new(context()['binding'],tmp_path)
    bad=context();bad['safety_after']['pump_armed']=True
    with pytest.raises(ValueError,match='unsafe'):store.record(s['session_id'],'fit',0,samples(0),bad)
    bad=context();bad['binding']['usb_serial']='different'
    with pytest.raises(ValueError,match='binding'):store.record(s['session_id'],'fit',0,samples(0),bad)
    for key in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):
        data=bridge();data['telemetry']['safety'][key]=True
        with pytest.raises(ValueError):safe_bridge(data)


def test_host_view_never_converts_without_validated_active_model(tmp_path):
    store,identifier=fitted(tmp_path);view=Hx711GramView(store.path,clock=lambda:100)
    state={'weight':{}}
    for i in range(12):view.apply(state,bridge(-565000,1000+i*1000))
    assert state['weight']['grams'] is None and state['weight']['calibrated'] is False
    assert state['weight']['calibration_state']=='NOT_CALIBRATED'


def test_host_view_needs_multiple_unique_fresh_samples_and_resets_after_reboot(tmp_path):
    store,identifier=activated(tmp_path);view=Hx711GramView(store.path,clock=lambda:100);state={'weight':{}}
    for _ in range(20):view.apply(state,bridge(-565000,1000))
    assert state['weight']['grams'] is None and state['weight']['raw_window_samples']==1
    for i in range(1,10):view.apply(state,bridge(-565000,1000+i*1000))
    assert state['weight']['grams']==pytest.approx(35,abs=.001) and state['weight']['stable'] is True
    assert state['weight']['controller_calibration_state']=='UNCHANGED_NOT_AUTHORIZED_FOR_ACTUATION'
    view.apply(state,bridge(-565000,500,host='new_host'))
    assert state['weight']['grams'] is None and state['weight']['stability_state']=='WARMING_UP'
    for i in range(1,10):view.apply(state,bridge(-565000,500+i*1000,host='new_host'))
    assert state['weight']['grams']==pytest.approx(35,abs=.001)
    unavailable=bridge(-565000,11000);unavailable['telemetry_usable_now']=False
    view.apply(state,unavailable);assert state['weight']['grams'] is None


def test_host_view_binding_mismatch_stale_and_outside_validated_range_hide_grams(tmp_path):
    store,identifier=activated(tmp_path);view=Hx711GramView(store.path,clock=lambda:100);state={'weight':{}}
    for i in range(10):view.apply(state,bridge(-560000,1000+i*1000))
    assert state['weight']['calibration_state']=='OUT_OF_VALIDATED_RANGE' and state['weight']['grams'] is None
    data=bridge();data['usb_serial']='changed';view.apply(state,data)
    assert state['weight']['calibration_state']=='DEVICE_BINDING_MISMATCH' and state['weight']['grams'] is None
    data=bridge();data['last_rx_monotonic_ms']=90000;view.apply(state,data)
    assert state['weight']['grams'] is None and state['weight']['age_seconds']==10


def test_api_read_only_unknown_no_calibration_and_no_mutation_endpoints(tmp_path):
    path=tmp_path/'state.db'
    with TestClient(create_app(db_path=path)) as client:
        body=client.get('/api/hx711/status').json()
        assert body['hx711']['grams'] is None and body['actual_dispensed_grams'] is None
        assert body['hx711']['calibration_authority']=='JETSON_SQLITE_PHYSICAL_REFERENCE_V1'
        assert client.post('/api/hx711/calibration',json={'grams_per_count':1}).status_code==405
        assert client.get('/api/hx711/calibration').json()['active'] is None
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
        assert db.execute('SELECT COUNT(*) FROM feed_requests').fetchone()[0]==0


def test_failed_validation_can_start_new_round_without_deleting_evidence(tmp_path):
    store,identifier=fitted(tmp_path)
    for mass in (*MASSES,0):store.record(identifier,'verify',mass,samples(mass+1 if mass==5 else mass),context())
    with pytest.raises(ValueError):store.activate(identifier,context())
    before=len(store.points(identifier));store.reset_phase(identifier,'verify')
    for mass in (*MASSES,0):store.record(identifier,'verify',mass,samples(mass),context())
    assert store.activate(identifier,context())['validation_passed']
    assert len(store.points(identifier))==before+7


def test_restart_before_activation_is_not_post_save_persistence_evidence(tmp_path):
    store,identifier=fitted(tmp_path)
    for mass in (*MASSES,0):store.record(identifier,'verify',mass,samples(mass),context(host='boot_b'))
    store.activate(identifier,context(host='boot_b'))
    for mass in (0,35,0):store.record(identifier,'persistence',mass,samples(mass),context(host='boot_b'))
    with pytest.raises(ValueError,match='restart after activation'):store.finish(identifier,True)


def test_capacity_limit_and_zero_first_are_explicit(tmp_path):
    store=CalibrationStore(tmp_path/'state.db');s=store.new(context()['binding'],tmp_path,capacity_g=20)
    with pytest.raises(ValueError,match='TEST0'):store.record(s['session_id'],'fit',5,samples(5),context())
    store.record(s['session_id'],'fit',0,samples(0),context())
    with pytest.raises(ValueError,match='capacity'):store.record(s['session_id'],'fit',35,samples(35),context())


def test_valid_model_does_not_make_unstable_window_a_stable_weight(tmp_path):
    store,identifier=activated(tmp_path);view=Hx711GramView(store.path,clock=lambda:100);state={'weight':{}}
    for i in range(10):view.apply(state,bridge(-590000+(300 if i%2 else 0),1000+i*1000))
    assert state['weight']['stable'] is False and state['weight']['stability_state']=='UNSTABLE'
    assert state['weight']['spread_grams']>.2


def test_active_calibration_reaches_same_systemstate_api_without_promoting_controller(tmp_path):
    from test_system_state import store as store_esp
    store,identifier=activated(tmp_path);store_esp(store.path)
    with TestClient(create_app(db_path=store.path)) as client:
        for i in range(10):
            with closing(sqlite3.connect(store.path)) as db:
                value=json.loads(db.execute('SELECT body FROM esp32_latest').fetchone()[0])
                value.update(usb_serial='5C85066678',usb_vid='1a86',usb_pid='55d3',last_rx_monotonic_ms=time.monotonic()*1000,updated_monotonic_ms=time.monotonic()*1000)
                value['telemetry']['monotonic_ms']=1000+i*1000
                value['telemetry']['sensors']['hx711']['raw_counts']=-565000
                db.execute('UPDATE esp32_latest SET body=? WHERE id=1',(json.dumps(value),));db.commit()
            state=client.get('/api/status').json()
        assert state['weight']['grams']==pytest.approx(35,abs=.001)
        assert state['weight']['stable'] is True and state['weight']['calibration_valid'] is True
        assert state['weight']['firmware_calibrated'] is False
        assert state['decisions']['consumed_grams'] is None and state['decisions']['eating_grams_validated'] is False
        assert state['safety']['actuator_execution'] is False
        endpoint=client.get('/api/hx711/status').json()
        assert endpoint['hx711']['raw']==-565000 and endpoint['hx711']['grams']==pytest.approx(35,abs=.001)
        assert endpoint['actual_dispensed_grams'] is None


def test_operator_cli_help_never_captures_or_opens_hardware(tmp_path):
    import hashlib
    from tools.hx711_calibration import write_raw_evidence, measurement_fields
    target=tmp_path/'synthetic_raw.json';write_raw_evidence(target,{'raw':[-1,0,1],'scope':'SYNTHETIC_ONLY'})
    assert target.with_name(target.name+'.sha256').read_text()==hashlib.sha256(target.read_bytes()).hexdigest()
    model={'tare_offset_counts':0,'grams_per_count':.001,'calibration_state':'CALIBRATED_PENDING_PERSISTENCE'}
    stats={'mean_raw':60000,'spread_counts':0,'stddev_counts':0,'drift_counts':0}
    reading=measurement_fields(model,None,stats,CRITERIA)
    assert reading['grams'] is None and reading['out_of_range_estimate_g']==60 and reading['calibration_state']=='OUT_OF_VALIDATED_RANGE'
    script=Path(__file__).resolve().parents[1]/'tools/hx711_calibration.py'
    result=subprocess.run([sys.executable,str(script),'capture','--help'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    assert result.returncode==0 and b'--mass-g' in result.stdout and b'--session' in result.stdout
