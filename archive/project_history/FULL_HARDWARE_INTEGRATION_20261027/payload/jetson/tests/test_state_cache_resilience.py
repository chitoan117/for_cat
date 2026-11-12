"""Synthetic SQLite/cache/API fault cases. Never opens serial, camera or actuators."""
import json
import logging
import sqlite3
from contextlib import closing

from fastapi.testclient import TestClient
import pytest

from app.ai_state import AiStateReader
from app.device_state import Esp32StateReader
from app import device_state
from app.main import create_app
from app.system_state import RealHardwareProvider, SystemStateService, unknown_state


def bridge_state():
    return {'health': 'ESP32_CONNECTED', 'serial_connected': True,
            'host_boot_id': 'synthetic-cache-boot', 'updated_monotonic_ms': 100000,
            'time_valid': False, 'serial_tx_enabled': False, 'actuator_execution': False,
            'telemetry': {'sensors': {'hx711': {'raw_counts': -700000, 'health': 'NOT_CALIBRATED'}},
                          'safety': {'servo_armed': False, 'pump_armed': False}},
            'decisions': {'mode': 'DRY_RUN_ONLY', 'food_behavior': 'IDLE', 'near_stable': True,
                          'actuator_execution': False, 'consumed_grams': None}}


def write_row(path, table, body):
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS '+table+'(id INTEGER PRIMARY KEY,body TEXT)')
        db.execute('INSERT OR REPLACE INTO '+table+' VALUES(1,?)', (body if isinstance(body, str) else json.dumps(body),))
        db.commit()


def test_no_kernel_identity_is_unknown_not_startup_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(device_state, 'read_host_boot_id', lambda: None)
    monkeypatch.setattr('app.ai_state.read_host_boot_id', lambda: None)
    path = tmp_path / 'missing.db'
    assert Esp32StateReader(path).status()['reader_error'] == 'HOST_BOOT_ID_UNAVAILABLE'
    assert AiStateReader(path).status()['classification'] == 'UNKNOWN'
    assert not path.exists()
    with TestClient(create_app(db_path=tmp_path / 'api.db')) as client:
        state = client.get('/api/status').json()
        assert state['data_source'] == 'REAL' and state['esp32']['connected'] is False
        assert state['weight']['grams'] is None and state['safety']['servo_armed'] is None


@pytest.mark.parametrize('body', [
    '[]', 'null', '{broken', '{"health":"ESP32_CONNECTED","health":"ESP32_DISCONNECTED"}',
    '{"value":NaN}', '[' * 1100 + '0' + ']' * 1100,
])
def test_corrupt_cache_json_fails_closed(tmp_path, body):
    path = tmp_path / 'cache.db'
    write_row(path, 'esp32_latest', body)
    state = Esp32StateReader(path, monotonic=lambda: 100, boot_id='synthetic-cache-boot').status()
    assert state['health'] == 'ESP32_DISCONNECTED' and state['telemetry_usable_now'] is False
    assert state['telemetry'] is None and state['actuator_execution'] is False


@pytest.mark.parametrize('change', [
    lambda s: s['telemetry'].update(sensors=[]),
    lambda s: s['telemetry']['sensors'].update(hx711=[]),
    lambda s: s['telemetry']['sensors']['hx711'].update(raw_counts=True),
    lambda s: s['telemetry']['sensors']['hx711'].update(raw_counts=9000000),
    lambda s: s['telemetry']['sensors']['hx711'].update(health=True),
    lambda s: s['telemetry']['sensors']['hx711'].update(health='ASSUMED'),
    lambda s: s['telemetry']['sensors'].update(approach={'distance_valid': True, 'distance_cm': None}),
    lambda s: s['telemetry']['sensors'].update(approach={'distance_valid': False, 'distance_cm': 25}),
    lambda s: s['telemetry']['sensors'].update(pir={'motion': 'true'}),
    lambda s: s['telemetry']['sensors'].update(button={'request_count': -1}),
    lambda s: s['telemetry']['safety'].update(servo_armed=True),
    lambda s: s['telemetry']['safety'].update(actuator_outputs_enabled=True),
    lambda s: s.update(decisions=[]),
    lambda s: s['decisions'].update(actuator_execution=True),
    lambda s: s.update(updated_monotonic_ms=True),
])
def test_malformed_cached_shapes_do_not_become_live_values(tmp_path, change):
    path = tmp_path / 'cache.db'
    body = bridge_state()
    change(body)
    write_row(path, 'esp32_latest', body)
    reader = Esp32StateReader(path, monotonic=lambda: 100, boot_id='synthetic-cache-boot')
    state = RealHardwareProvider(reader).snapshot()
    assert state['esp32']['connected'] is False
    assert state['weight']['raw_counts'] is None and state['weight']['grams'] is None
    assert state['safety']['servo_armed'] is None and state['safety']['actuator_execution'] is False


@pytest.mark.parametrize('body', [
    [], None, {'classification': 'CAT', 'confidence': True},
    {'classification': 'CAT', 'confidence': 1.1}, {'classification': 'NONE', 'confidence': .5},
    {'classification': 'CAT', 'confidence': .9, 'updated_monotonic_ms': True},
    {'classification': 'UNKNOWN', 'confidence': None},
])
def test_bad_ai_cache_never_becomes_fake_cat_or_none(tmp_path, body):
    path = tmp_path / 'ai.db'
    if isinstance(body, dict):
        complete = {'health': 'ONLINE', 'actuator_execution': False, 'host_boot_id': 'synthetic-cache-boot',
                    'updated_monotonic_ms': 100000, 'last_observation_at': 'synthetic'}
        complete.update(body)
    else:
        complete = body
    write_row(path, 'ai_latest', complete)
    assert AiStateReader(path, monotonic=lambda: 100, boot_id='synthetic-cache-boot').status()['classification'] == 'UNKNOWN'


def test_missing_ai_is_unknown_behavior_without_changing_water_policy(tmp_path):
    path = tmp_path / 'state.db'
    body = bridge_state()
    body['decisions'].update(water_request_preview=True, water_reason='SYNTHETIC_DRY_RUN', consumed_grams=12)
    write_row(path, 'esp32_latest', body)
    reader = Esp32StateReader(path, monotonic=lambda: 100, boot_id='synthetic-cache-boot')
    state = RealHardwareProvider(reader).snapshot()
    assert state['decisions']['food_behavior'] == 'UNKNOWN'
    assert state['decisions']['fsm_internal_state'] == 'IDLE'
    assert state['decisions']['near_stable'] is False
    assert state['decisions']['consumed_grams'] is None
    assert state['decisions']['water_request_preview'] is True
    assert state['decisions']['actuator_execution'] is False


def test_one_bad_history_row_does_not_hide_valid_history(tmp_path):
    path = tmp_path / 'events.db'
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE esp32_events(seq INTEGER PRIMARY KEY,kind TEXT,occurred_at TEXT,body TEXT)')
        db.executemany('INSERT INTO esp32_events VALUES(?,?,?,?)', [
            (1, 'synthetic', 't', '{broken'), (2, 'synthetic', 't', '{"valid":true}')])
        db.commit()
    rows = Esp32StateReader(path, boot_id='synthetic-cache-boot').events()
    assert len(rows) == 1 and rows[0]['seq'] == 2


def test_uncalibrated_cached_eating_is_not_an_observed_eating_claim(tmp_path):
    class SyntheticCatReader:
        def status(self):
            return {'classification': 'CAT', 'health': 'ONLINE', 'confidence': .9}
    path = tmp_path / 'uncalibrated.db'
    body = bridge_state()
    body['decisions']['food_behavior'] = 'EATING'
    write_row(path, 'esp32_latest', body)
    state = RealHardwareProvider(Esp32StateReader(path, monotonic=lambda: 100, boot_id='synthetic-cache-boot'), SyntheticCatReader()).snapshot()
    assert state['decisions']['fsm_internal_state'] == 'EATING'
    assert state['decisions']['food_behavior'] == 'UNKNOWN'
    assert state['decisions']['consumed_grams'] is None and state['weight']['grams'] is None


def test_rest_and_ws_survive_provider_failure_and_recover(tmp_path, caplog):
    class FlakyProvider:
        data_source = 'REAL'
        failing = True
        def snapshot(self):
            if self.failing:
                raise RuntimeError('synthetic provider fault')
            state = unknown_state('REAL')
            state['recovered_fixture'] = True
            return state
    provider = FlakyProvider()
    service = SystemStateService(provider)
    with caplog.at_level(logging.ERROR):
        for _ in range(5):
            assert service.snapshot()['data_source'] == 'REAL'
    assert len([r for r in caplog.records if 'provider unavailable' in r.message]) == 1
    app = create_app(db_path=tmp_path / 'service.db')
    app.state.system_state = service
    with TestClient(app) as client:
        assert client.get('/api/status').json()['provider_error'] == 'RuntimeError'
        with client.websocket_connect('/api/ws/state') as ws:
            first = ws.receive_json()
            assert first['esp32']['connected'] is False and first['weight']['grams'] is None
            provider.failing = False
            for _ in range(6):
                recovered = ws.receive_json()
                if recovered.get('recovered_fixture'):
                    break
            assert recovered['recovered_fixture'] is True and recovered['data_source'] == 'REAL'
            assert not service.task.done()
