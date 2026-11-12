import sqlite3
import json
from contextlib import closing

from fastapi.testclient import TestClient
import pytest

from app.dry_run_requests import DryRunRequests
from app.main import create_app


def test_durable_request_idempotency_conflicts_and_target(tmp_path):
    path = tmp_path / 'dry.db'
    requests = DryRunRequests(path)
    first = requests.enqueue('one', 'MANUAL', 'APP')
    assert first['request']['target_grams'] == 35 and first['decision'] is None
    assert requests.enqueue('one', 'MANUAL', 'APP') == first
    with pytest.raises(ValueError):
        requests.enqueue('one', 'MANUAL', 'KIOSK')
    for grams in (0, 40, True):
        with pytest.raises(ValueError):
            requests.enqueue('bad', 'MANUAL', 'APP', grams)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0] == 1


def test_inbox_capacity_fails_closed_without_id_eviction(tmp_path):
    requests = DryRunRequests(tmp_path / 'bounded.db')
    for i in range(256):
        requests.enqueue(str(i), 'MANUAL', 'APP')
    with pytest.raises(OverflowError):
        requests.enqueue('full', 'MANUAL', 'APP')
    assert requests.enqueue('0', 'MANUAL', 'APP')['request']['request_id'] == '0'


def test_preview_api_is_only_manual_and_never_records_a_real_feed(tmp_path, monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED', '1')
    path = tmp_path / 'canonical.db'
    with TestClient(create_app(db_path=path)) as client:
        result = client.post('/api/feed/preview', json={'request_id': 'demo', 'sub_source': 'KIOSK'})
        assert result.status_code == 202
        assert result.json()['request']['source'] == 'MANUAL'
        assert result.json()['request']['actuator_execution'] is False
        assert result.json()['request']['actual_dispensed_grams'] is None
        assert client.post('/api/feed/preview', json={'request_id': 'bad', 'sub_source': 'APP', 'target_grams': 40}).status_code == 422
        assert client.post('/api/feed/preview', json={'request_id': 'bad', 'sub_source': 'BUTTON'}).status_code == 422
        assert client.get('/api/feed/preview/demo').json()['decision'] is None
        assert client.post('/api/feed/manual').status_code == 404
        assert client.post('/api/v1/feed/manual').status_code == 503
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT COUNT(*) FROM feed_requests').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0


def test_preview_api_retry_returns_same_cpp_decision_and_refuses_source_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED', '1')
    path = tmp_path / 'retry.db'
    body = {'request_id': 'ui-safe-retry', 'sub_source': 'APP', 'target_grams': 35}
    with TestClient(create_app(db_path=path)) as client:
        first = client.post('/api/feed/preview', json={**body, 'source': 'AUTO_CAT'}).json()
        assert first['request']['source'] == 'MANUAL'
        decision = {'request_id': body['request_id'], 'source': 'MANUAL', 'sub_source': 'APP',
                    'target_grams': 35, 'status': 'DRY_RUN_BLOCKED', 'reason': 'UNATTENDED_SAFE_MODE',
                    'qualification_reason': 'WEIGHT_NOT_CALIBRATED', 'actuator_execution': False,
                    'actual_dispensed_grams': None}
        with closing(sqlite3.connect(path)) as db:
            db.execute('UPDATE feed_dry_run_requests SET decision=? WHERE request_id=?', (json.dumps(decision), body['request_id']))
            db.commit()
        again = client.post('/api/feed/preview', json=body).json()
        assert again['request'] == first['request'] and again['decision'] == decision
        assert client.post('/api/feed/preview', json={**body, 'sub_source': 'KIOSK'}).status_code == 409
        assert client.get('/api/feed/preview/'+body['request_id']).json() == again
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM feed_requests').fetchone()[0] == 0
