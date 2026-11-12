from datetime import datetime, timezone
from types import SimpleNamespace
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.dry_run_requests import DryRunRequests
from app.meal_plans import CreatePlan, UpdatePlan, MealPlans, PlanConflict, PlanMissing, preview_plan
import app.api.meal_plan_routes as routes


def definition(**changes):
    return {'plan_id': 'plan_test', 'name': 'Bữa tối', 'local_time': '22:50',
            'weekdays': [6], 'target_grams': 35, 'timezone': 'Asia/Ho_Chi_Minh', 'enabled': False, **changes}


def safe_state():
    return {'data_source': 'REAL', 'esp32': {'connected': True}, 'time': {'time_valid': True},
            'safety': {**{key: False for key in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water', 'actuator_execution')}, 'actuator_outputs_enabled': 0}}


def test_persistent_crud_revision_idempotency_and_existing_schema_unchanged(tmp_path):
    path = tmp_path/'state.db'
    with sqlite3.connect(path) as db:
        db.executescript("PRAGMA user_version=2; CREATE TABLE original(value TEXT); INSERT INTO original VALUES('keep');")
    plans = MealPlans(path)
    request = CreatePlan(**definition())
    first = plans.create(request)
    assert plans.create(request) == first and first['revision'] == 1
    assert MealPlans(path).list()['plans'] == [first]
    changed = definition(name='Bữa sáng', local_time='07:00'); changed.pop('plan_id')
    second = plans.update(first['plan_id'], UpdatePlan(**changed, expected_revision=1))
    assert second['revision'] == 2 and second['local_time'] == '07:00'
    with pytest.raises(PlanConflict):
        plans.update(first['plan_id'], UpdatePlan(**changed, expected_revision=1))
    with pytest.raises(PlanConflict):
        plans.delete(first['plan_id'], 1)
    assert plans.delete(first['plan_id'], 2)['deleted']
    assert plans.delete(first['plan_id'], 2)['deleted']  # lost DELETE reply retry
    with pytest.raises(PlanConflict):
        plans.create(request)  # a stale POST must not resurrect the deleted identity
    with pytest.raises(PlanMissing):
        plans.get(first['plan_id'])
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert db.execute('SELECT value FROM original').fetchone()[0] == 'keep'


@pytest.mark.parametrize('changes', [
    {'target_grams': 40}, {'target_grams': 35.0}, {'enabled': 1}, {'local_time': '24:00'},
    {'local_time': '7:00'}, {'weekdays': []}, {'weekdays': [True]}, {'weekdays': [0, 0]},
    {'weekdays': [7]}, {'name': '  '}, {'timezone': 'UTC'}, {'pump_on': True}, {'plan_id': '../x'},
])
def test_invalid_configuration_never_creates_plan(tmp_path, changes):
    with TestClient(create_app(db_path=tmp_path/'state.db')) as client:
        assert client.post('/api/meal-plans', json=definition(**changes)).status_code == 422
        assert client.get('/api/meal-plans').json()['plans'] == []


def test_capacity_tombstones_and_corrupt_row_isolation(tmp_path):
    path = tmp_path/'state.db'; plans = MealPlans(path)
    plans.MAX_ACTIVE = 2; plans.MAX_IDENTITIES = 3
    plans.create(CreatePlan(**definition(plan_id='one')))
    plans.create(CreatePlan(**definition(plan_id='two')))
    with pytest.raises(OverflowError):
        plans.create(CreatePlan(**definition(plan_id='three')))
    plans.delete('one', 1); plans.create(CreatePlan(**definition(plan_id='three')))
    plans.delete('two', 1)
    with pytest.raises(OverflowError):
        plans.create(CreatePlan(**definition(plan_id='four')))
    with sqlite3.connect(path) as db:
        db.execute("UPDATE meal_plans SET body=? WHERE plan_id='three'", ('{"name":"bad","name":"duplicate"}',))
    result = plans.list()
    assert result['plans'] == [] and len(result['errors']) == 1


@pytest.mark.parametrize('case,reason', [
    ('disabled', 'PLAN_DISABLED'), ('wrong_day', 'NOT_SCHEDULED_TODAY'), ('future', 'NOT_DUE'),
    ('missed', 'MISSED_WINDOW_NO_CATCHUP'), ('time_invalid', 'TIME_INVALID'),
    ('offline', 'ESP32_UNAVAILABLE_NO_QUEUE'), ('unsafe', 'SAFETY_STATE_UNKNOWN_OR_UNSAFE_NO_QUEUE'),
])
def test_ineligible_schedule_never_enqueues(tmp_path, case, reason):
    plans = MealPlans(tmp_path/'state.db'); item = definition(enabled=True)
    state = safe_state(); now = datetime(2026,10,25,15,50,10,tzinfo=timezone.utc)
    if case == 'disabled':item['enabled'] = False
    if case == 'wrong_day':item['weekdays'] = [0]
    if case == 'future':item['local_time'] = '22:51'
    if case == 'missed':item['local_time'] = '22:48'
    if case == 'time_invalid':state['time']['time_valid'] = False
    if case == 'offline':state['esp32']['connected'] = False
    if case == 'unsafe':state['safety']['pump_armed'] = True
    plan = plans.create(CreatePlan(**item))
    result = preview_plan(plan, DryRunRequests(tmp_path/'must_not_exist.db'), state, now)
    assert result['reason'] == reason and result['candidate'] is False
    assert not (tmp_path/'must_not_exist.db').exists()


def test_vietnam_midnight_weekday_and_same_due_id_after_reopen(tmp_path):
    path = tmp_path/'state.db'; plans = MealPlans(path)
    plan = plans.create(CreatePlan(**definition(local_time='00:00', weekdays=[0], enabled=True)))
    now = datetime(2026,10,25,17,0,10,tzinfo=timezone.utc)  # Monday00:00 in Vietnam
    first = preview_plan(plan, DryRunRequests(path), safe_state(), now)
    again = preview_plan(MealPlans(path).get(plan['plan_id']), DryRunRequests(path), safe_state(), now)
    assert first['candidate'] and first['due_at'].startswith('2026-10-26T00:00:00+07:00')
    assert first['request'] == again['request']
    request = first['request']['request']
    assert request['source'] == 'SCHEDULED' and request['sub_source'] == '' and request['target_grams'] == 35
    assert request['actuator_execution'] is False and request['actual_dispensed_grams'] is None
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0] == 1


def test_real_api_explicit_preview_revision_guard_and_no_autonomous_worker(tmp_path, monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED', '1')
    now = datetime(2026,10,25,15,50,10,tzinfo=timezone.utc)
    monkeypatch.setattr(routes, 'datetime', SimpleNamespace(now=lambda tz: now))
    app = create_app(db_path=tmp_path/'state.db')
    with TestClient(app) as client:
        monkeypatch.setattr(app.state.system_state, 'snapshot', safe_state)
        created = client.post('/api/meal-plans', json=definition(enabled=True))
        assert created.status_code == 201
        assert client.get('/api/meal-plans').json()['autonomous_worker_enabled'] is False
        wrong = client.post('/api/meal-plans/plan_test/preview', json={'expected_revision': 2})
        assert wrong.status_code == 409
        first = client.post('/api/meal-plans/plan_test/preview', json={'expected_revision': 1})
        assert first.status_code == 200 and first.json()['candidate'] is True
        again = client.post('/api/meal-plans/plan_test/preview', json={'expected_revision': 1})
        assert again.json()['request'] == first.json()['request']
        assert client.request('DELETE', '/api/meal-plans/plan_test', json={'expected_revision': 1}).status_code == 200
        assert client.post('/api/meal-plans/plan_test/preview', json={'expected_revision': 1}).status_code == 404
