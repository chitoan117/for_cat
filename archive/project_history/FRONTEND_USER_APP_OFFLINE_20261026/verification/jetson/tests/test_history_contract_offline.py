"""Existing API/SQLite contracts in isolated fixtures, not new production routes."""
from datetime import datetime,timezone
import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import create_app
from app.meal_plans import MealPlans,CreatePlan
from app.scheduled_worker import ScheduledOccurrences

def test_durable_occurrence_is_exposed_even_after_event_ring_is_empty(tmp_path,monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1')
    path=tmp_path/'isolated.db'
    app=create_app(db_path=path,scheduled_worker_enabled=False)
    plan=MealPlans(path).create(CreatePlan(plan_id='fixture_history',name='Fixture only',local_time='09:30',weekdays=[0],enabled=True))
    state={'data_source':'REAL','time':{'time_valid':True},'esp32':{'connected':True},
           'safety':{**{k:False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution')},'actuator_outputs_enabled':0}}
    result=ScheduledOccurrences(path).submit(plan['plan_id'],state,datetime(2026,10,26,2,30,10,tzinfo=timezone.utc),origin='WORKER')
    with TestClient(app) as client:
        assert client.get('/api/v1/esp32/events').json()==[]
        history=client.get('/api/meal-plans').json()['recent_occurrences']
        assert len(history)==1 and history[0]['request_id']==result['request']['request']['request_id']
        assert history[0]['origin']=='WORKER' and history[0]['decision'] is None
        assert history[0]['actuator_execution'] is False and history[0]['actual_dispensed_grams'] is None

def test_manual_dry_run_and_system_events_have_true_timestamps_and_no_completion(tmp_path,monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1')
    path=tmp_path/'isolated.db';app=create_app(db_path=path,scheduled_worker_enabled=False)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE esp32_events(seq INTEGER PRIMARY KEY,kind TEXT,occurred_at TEXT,body TEXT)')
        body={'request_id':'fixture_manual','source':'MANUAL','target_grams':35,'status':'DRY_RUN_BLOCKED','qualification_reason':'WEIGHT_NOT_CALIBRATED','actuator_execution':False,'actual_dispensed_grams':None}
        db.execute('INSERT INTO esp32_events VALUES(1,?,?,?)',('feed_request_dry_run','2026-10-26T02:30:00Z',json.dumps(body)))
        db.execute('INSERT INTO esp32_events VALUES(2,?,?,?)',('serial_disconnected','2026-10-26T02:31:00Z',json.dumps({'reason':'SERIAL_HUP'})))
    with TestClient(app) as client:
        events=client.get('/api/v1/esp32/events?limit=100').json()
        assert events[0]['kind']=='serial_disconnected' and events[0]['timestamp']=='2026-10-26T02:31:00Z'
        assert events[1]['details']['actual_dispensed_grams'] is None
        assert client.get('/api/status').json()['weight']['grams'] is None
