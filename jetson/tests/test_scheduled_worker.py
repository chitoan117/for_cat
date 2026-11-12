"""Isolated SQLite/fake-clock tests plus actual C++ arbiter on synthetic PTY."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3
from threading import RLock
import time

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.meal_plans import CreatePlan, UpdatePlan, MealPlans
from app.scheduled_worker import ScheduledOccurrences, ScheduledWorker

NOW = datetime(2026,10,26,2,30,10,tzinfo=timezone.utc)  # Monday09:30 Vietnam


def safe():
    return {'schema_version':'system_state_v1','data_source':'REAL','time':{'time_valid':True},
            'esp32':{'connected':True,'health':'ESP32_CONNECTED','stale':False},
            'safety':{**{k:False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution')},'actuator_outputs_enabled':0}}


def plan(path, identifier='meal_a', **overrides):
    return MealPlans(path).create(CreatePlan(**{'plan_id':identifier,'name':'Synthetic test meal',
        'local_time':'09:30','weekdays':[0],'enabled':True,**overrides}))


def worker(path, clock=lambda:NOW, snapshot=safe):
    return ScheduledWorker(path,snapshot,RLock(),enabled=True,clock=clock)


def rows(path, table):
    with closing(sqlite3.connect(path)) as db:
        return db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]


def test_not_due_then_due_repeated_polls_and_restart_have_one_request(tmp_path):
    path=tmp_path/'state.db';plan(path);w=worker(path)
    assert w.tick(now=NOW-timedelta(minutes=1))==[]
    assert rows(path,'feed_dry_run_requests')==0
    first=w.tick()[0];identifier=first['request']['request']['request_id']
    assert first['occurrence_state']=='SUBMITTED'
    for _ in range(10):
        assert w.tick()[0]['request']['request']['request_id']==identifier
    restarted=worker(path)
    assert restarted.worker_id!=w.worker_id
    assert restarted.tick()[0]['occurrence_state']=='ALREADY_SUBMITTED'
    assert rows(path,'feed_dry_run_requests')==rows(path,'scheduled_occurrences')==1
    body=first['request']['request']
    assert body['source']=='SCHEDULED' and body['target_grams']==35
    assert body['actuator_execution'] is False and body['actual_dispensed_grams'] is None


@pytest.mark.parametrize('case',['disabled','deleted','wrong_day'])
def test_disabled_deleted_wrong_day_do_not_submit(tmp_path,case):
    path=tmp_path/'state.db';p=plan(path,enabled=case!='disabled',weekdays=[1] if case=='wrong_day' else [0])
    if case=='deleted':MealPlans(path).delete(p['plan_id'],p['revision'])
    assert worker(path).tick()==[]
    assert rows(path,'feed_dry_run_requests')==rows(path,'scheduled_occurrences')==0


def test_many_plans_same_minute_each_have_one_occurrence(tmp_path):
    path=tmp_path/'state.db'
    for identifier in ('one','two','three'):plan(path,identifier)
    w=worker(path);first=w.tick();again=w.tick()
    assert len(first)==len(again)==3
    assert len({r['occurrence_id'] for r in first})==3
    assert rows(path,'feed_dry_run_requests')==rows(path,'scheduled_occurrences')==3


def test_revision_and_retime_after_submission_do_not_duplicate_same_vietnam_day(tmp_path):
    path=tmp_path/'state.db';p=plan(path);w=worker(path);first=w.tick()[0]
    values={key:p[key] for key in ('name','local_time','weekdays','enabled','target_grams','timezone')}
    p=MealPlans(path).update(p['plan_id'],UpdatePlan(**{**values,'name':'Edited label'},expected_revision=1))
    assert w.tick()[0]['request']==first['request']
    p=MealPlans(path).update(p['plan_id'],UpdatePlan(**{**values,'local_time':'09:31'},expected_revision=2))
    result=w.tick(now=NOW+timedelta(minutes=1))[0]
    assert result['occurrence_id']==first['occurrence_id'] and result['request']==first['request']
    assert result['occurrence_plan_revision']==1
    assert rows(path,'feed_dry_run_requests')==1


def test_update_before_submission_uses_current_config_and_delete_race_is_safe(tmp_path,monkeypatch):
    path=tmp_path/'state.db';p=plan(path);w=worker(path)
    values={key:p[key] for key in ('name','local_time','weekdays','enabled','target_grams','timezone')}
    MealPlans(path).update(p['plan_id'],UpdatePlan(**{**values,'local_time':'09:31'},expected_revision=1))
    assert w.tick()==[]
    assert w.tick(now=NOW+timedelta(minutes=1))[0]['occurrence_state']=='SUBMITTED'
    other=plan(path,'deleted_between_scan_and_submit')
    store=w.occurrences();original=store.submit
    def deleting(identifier,*args,**kwargs):
        if identifier==other['plan_id']:store.plans.delete(identifier,1)
        return original(identifier,*args,**kwargs)
    monkeypatch.setattr(store,'submit',deleting)
    w.tick()
    assert rows(path,'feed_dry_run_requests')==1


def test_vietnam_midnight_weekday_and_next_day_occurrence(tmp_path):
    path=tmp_path/'state.db';plan(path,local_time='00:00',weekdays=list(range(7)))
    first_time=datetime(2026,10,25,17,0,10,tzinfo=timezone.utc)
    w=worker(path);first=w.tick(now=first_time)[0]
    second=w.tick(now=first_time+timedelta(days=1))[0]
    assert first['local_date']=='2026-10-26' and first['due_at'].startswith('2026-10-26T00:00:00+07:00')
    assert second['local_date']=='2026-10-27' and first['occurrence_id']!=second['occurrence_id']
    assert rows(path,'feed_dry_run_requests')==2


@pytest.mark.parametrize('case',['invalid_time','offline','stale','mock','servo_armed','pump_armed',
 'auto_feed','auto_water','actuator_execution','unknown_safety','outputs_enabled'])
def test_unavailable_time_or_unsafe_state_never_enqueues(tmp_path,case):
    path=tmp_path/'state.db';plan(path);state=safe()
    if case=='invalid_time':state['time']['time_valid']=False
    elif case=='offline':state['esp32']['connected']=False
    elif case=='stale':state['esp32']['stale']=True
    elif case=='mock':state['data_source']='MOCK'
    elif case=='unknown_safety':state['safety']['pump_armed']=None
    elif case=='outputs_enabled':state['safety']['actuator_outputs_enabled']=1
    else:state['safety'][case]=True
    w=worker(path,snapshot=lambda:state)
    assert w.tick()==[] and rows(path,'feed_dry_run_requests')==0
    assert rows(path,'scheduled_occurrences')==0
    assert w.status()['status'].startswith('WAITING_')


def test_retry_after_temporary_unavailable_only_within_window_and_no_catchup(tmp_path):
    path=tmp_path/'state.db';plan(path);w=worker(path);state=safe();state['esp32']['connected']=False
    assert w.tick(state=state)==[]
    assert len(w.tick(now=NOW+timedelta(seconds=20)))==1
    assert worker(path).tick(now=NOW+timedelta(minutes=2))==[]
    assert rows(path,'feed_dry_run_requests')==1


def test_occurrence_insert_failure_rolls_back_inbox_and_retry_is_atomic(tmp_path):
    path=tmp_path/'state.db';plan(path);w=worker(path);w.occurrences()
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TRIGGER injected BEFORE INSERT ON scheduled_occurrences BEGIN SELECT RAISE(ABORT,'test only'); END")
        db.commit()
    assert w.tick()==[] and w.status()['status']=='DEGRADED'
    assert rows(path,'feed_dry_run_requests')==rows(path,'scheduled_occurrences')==0
    with closing(sqlite3.connect(path)) as db:db.execute('DROP TRIGGER injected');db.commit()
    assert len(w.tick())==1 and rows(path,'feed_dry_run_requests')==1


def test_full_inbox_creates_no_occurrence_then_retries_safely(tmp_path):
    from app.dry_run_requests import DryRunRequests
    path=tmp_path/'state.db';plan(path);w=worker(path);w.occurrences()
    for i in range(256):DryRunRequests(path).enqueue('fixture_'+str(i),'MANUAL','APP')
    assert w.tick()==[] and rows(path,'scheduled_occurrences')==0
    assert 'OverflowError' in w.status()['last_error']
    with closing(sqlite3.connect(path)) as db:db.execute("DELETE FROM feed_dry_run_requests WHERE request_id='fixture_0'");db.commit()
    assert len(w.tick())==1 and rows(path,'scheduled_occurrences')==1


def test_concurrent_workers_and_preview_share_one_transactional_identity(tmp_path):
    path=tmp_path/'state.db';p=plan(path);a,b=worker(path),worker(path);a.occurrences();b.occurrences()
    with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(lambda w:w.tick(),[a,b]))
    assert sum(r[0]['occurrence_state']=='SUBMITTED' for r in outcomes)==1
    preview=ScheduledOccurrences(path).submit(p['plan_id'],safe(),NOW,origin='PREVIEW',expected_revision=1)
    assert preview['occurrence_state']=='ALREADY_SUBMITTED'
    assert rows(path,'feed_dry_run_requests')==rows(path,'scheduled_occurrences')==1


def test_preview_first_worker_second_share_one_id_and_expired_lock_recheck(tmp_path):
    path=tmp_path/'state.db';p=plan(path);store=ScheduledOccurrences(path)
    preview=store.submit(p['plan_id'],safe(),NOW,origin='PREVIEW',expected_revision=1)
    assert worker(path).tick()[0]['request']==preview['request']
    plan(path,'expired')
    result=store.submit('expired',safe(),NOW,origin='WORKER',clock=lambda:NOW+timedelta(minutes=2))
    assert result['reason']=='MISSED_WINDOW_NO_CATCHUP' and rows(path,'feed_dry_run_requests')==1


def test_asgi_background_worker_creates_request_without_preview_post_and_stops(tmp_path,monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1')
    path=tmp_path/'state.db';app=create_app(db_path=path,scheduled_worker_enabled=True)
    plan(path);app.state.scheduled_worker.clock=lambda:NOW
    monkeypatch.setattr(app.state.system_state,'snapshot',safe)
    app.state.scheduled_worker.state_snapshot=safe  # explicit captured callback seam
    with TestClient(app) as client:
        end=time.monotonic()+4
        while True:
            status=client.get('/api/meal-plans/worker').json()
            if status['recent_occurrences']:break
            assert time.monotonic()<end;time.sleep(.05)
        assert status['worker']['running'] is True and status['worker']['enabled'] is True
        assert status['worker']['actuator_execution'] is False and status['worker']['auto_feed'] is False and status['worker']['auto_water'] is False
        assert status['recent_occurrences'][0]['origin']=='WORKER'
        assert rows(path,'feed_dry_run_requests')==1
        assert client.get('/api/meal-plans').json()['autonomous_worker_enabled'] is True
    assert app.state.scheduled_worker.status()['status']=='STOPPED'


@pytest.mark.parametrize('env',[
 {'SCHEDULED_DRY_RUN_WORKER_ENABLED':'bad'},
 {'SCHEDULED_DRY_RUN_WORKER_ENABLED':'1','ESP32_BRIDGE_ENABLED':'0'},
 {'SCHEDULED_DRY_RUN_WORKER_ENABLED':'1','ESP32_BRIDGE_ENABLED':'1','SYSTEM_STATE_PROVIDER':'MOCK'},
 {'SCHEDULED_DRY_RUN_POLL_SECONDS':'0'},
])
def test_invalid_worker_configuration_fails_before_database(tmp_path,monkeypatch,env):
    for key,value in env.items():monkeypatch.setenv(key,value)
    path=tmp_path/'not_opened.db'
    with pytest.raises(ValueError):create_app(db_path=path)
    assert not path.exists()


def test_worker_request_is_consumed_by_existing_cpp_arbiter_on_synthetic_pty(tmp_path):
    from test_esp32_bridge import Rig, wait_for
    rig=Rig(tmp_path)
    try:
        rig.send();wait_for(lambda:rig.state().get('health')=='ESP32_CONNECTED')
        now=datetime.now(timezone.utc);local=now.astimezone(timezone(timedelta(hours=7)))
        plan(rig.db,local_time=local.strftime('%H:%M'),weekdays=[local.weekday()])
        w=worker(rig.db,clock=lambda:now);first=w.tick()[0]
        request_id=first['request']['request']['request_id']
        event=wait_for(lambda:next((e for e in rig.events('feed_request_dry_run') if e.get('request_id')==request_id),None))
        assert event['source']=='SCHEDULED' and event['target_grams']==35
        assert event['actuator_execution'] is False and event['actual_dispensed_grams'] is None
        assert event['reason']=='UNATTENDED_SAFE_MODE'
        worker(rig.db,clock=lambda:now).tick();time.sleep(.2)
        assert len([e for e in rig.events('feed_request_dry_run') if e.get('request_id')==request_id])==1
        with pytest.raises(BlockingIOError):os.read(rig.master,4096)
    finally:
        rig.close()
