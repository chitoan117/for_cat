import json
import sqlite3
import time
from contextlib import closing

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.system_state import SystemStateService, MockProvider
from app import device_state


@pytest.fixture(autouse=True)
def synthetic_identity_for_non_linux_api_fixtures(monkeypatch):
    if device_state.read_host_boot_id() is None:
        monkeypatch.setattr(device_state, 'read_host_boot_id', lambda: 'synthetic-offline-boot')
        monkeypatch.setattr('app.ai_state.read_host_boot_id', lambda: 'synthetic-offline-boot')


def store(path, distance=24.8, health='ESP32_CONNECTED'):
    state = {'health': health, 'serial_connected': health == 'ESP32_CONNECTED',
             'host_boot_id': device_state.read_host_boot_id(),
             'updated_monotonic_ms': time.monotonic() * 1000,
             'actuator_execution': False, 'serial_tx_enabled': False, 'time_valid': True,
             'last_received_at': '2026-10-23T15:00:00Z', 'device': '/dev/SYNTHETIC_PTY_ONLY',
             'telemetry': {'mode': 'diag_current_hardware', 'monotonic_ms': 1000,
                           'sensors': {
                               'pir': {'configured': True, 'motion': False, 'transition_count': 2},
                               'approach': {'distance_valid': True, 'distance_cm': distance, 'health': 'NOT_CALIBRATED', 'timeout_count': 0},
                               'water_operational': {'distance_valid': False, 'distance_cm': None, 'health': 'NOT_CONFIGURED', 'timeout_count': 1},
                               'hx711': {'raw_counts': -700000, 'raw_available': True, 'firmware_calibrated': False, 'health': 'NOT_CALIBRATED'},
                               'oled': {'health': 'HEALTHY'},
                               'button': {'pressed': False, 'request_count': 3, 'health': 'HEALTHY'}},
                           'safety': {'servo_armed': False, 'pump_armed': False, 'auto_feed': False,
                                      'auto_water': False, 'actuator_outputs_enabled': 0}}}
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
        db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)', (json.dumps(state),))
        db.commit()


def test_real_default_no_hardware_never_mock_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv('SYSTEM_STATE_PROVIDER', raising=False)
    with TestClient(create_app(db_path=tmp_path / 'unknown.db')) as client:
        state = client.get('/api/status').json()
        assert state['data_source'] == 'REAL'
        assert state['esp32']['connected'] is False
        assert state['weight']['grams'] is None and state['weight']['calibrated'] is False
        assert state['approach']['distance_cm'] is None
        assert state['ai']['classification'] == 'UNKNOWN'
        assert state['food_reservoir_percent'] is None and state['food_reservoir_sensor'] == 'NOT_WIRED'
        assert state['safety']['servo_armed'] is None  # unknown, never a fabricated OFF


def test_real_rest_preserves_values_and_nulls(tmp_path, monkeypatch):
    monkeypatch.setenv('SYSTEM_STATE_PROVIDER', 'REAL')
    path = tmp_path / 'state.db'
    store(path)
    with TestClient(create_app(db_path=path)) as client:
        state = client.get('/api/status').json()
        assert state['esp32']['connected'] is True
        assert state['approach']['distance_cm'] == 24.8 and state['approach']['valid'] is True
        assert state['approach']['health'] == 'NOT_CALIBRATED'
        assert state['weight']['raw_counts'] == -700000 and state['weight']['grams'] is None
        assert state['manual_button']['request_count'] == 3
        assert state['water_operational']['distance_cm'] is None
        assert state['safety']['actuator_execution'] is False


def test_same_backend_rest_ws_updates_and_hides_disconnected_values(tmp_path, monkeypatch):
    monkeypatch.setenv('SYSTEM_STATE_PROVIDER', 'REAL')
    path = tmp_path / 'ws.db'
    store(path)
    with TestClient(create_app(db_path=path)) as client:
        with client.websocket_connect('/api/ws/state') as ws:
            assert ws.receive_json()['approach']['distance_cm'] == 24.8
            store(path, distance=32.5)
            for _ in range(6):
                state = ws.receive_json()
                if state['approach']['distance_cm'] == 32.5:
                    break
            assert state['approach']['distance_cm'] == client.get('/api/status').json()['approach']['distance_cm'] == 32.5
            store(path, health='ESP32_DISCONNECTED')
            for _ in range(6):
                state = ws.receive_json()
                if not state['esp32']['connected']:
                    break
            assert state['approach']['distance_cm'] is None and state['weight']['raw_counts'] is None
            assert state['safety']['servo_armed'] is None


def test_two_views_use_one_asset_api_and_no_serial_access(tmp_path):
    with TestClient(create_app(db_path=tmp_path / 'views.db')) as client:
        kiosk = client.get('/kiosk')
        app = client.get('/app')
        assert kiosk.status_code == app.status_code == 200
        assert kiosk.content == app.content
        js = client.get('/assets/system-state.js').text
        assert "fetch('/api/status'" in js and "'/api/ws/state'" in js
        assert 'navigator.serial' not in js and 'Math.random' not in js
        assert 'readings hidden' in js


def test_mock_is_explicit_and_labelled(tmp_path, monkeypatch):
    monkeypatch.setenv('SYSTEM_STATE_PROVIDER', 'MOCK')
    with TestClient(create_app(db_path=tmp_path / 'mock.db')) as client:
        assert client.get('/api/status').json()['data_source'] == 'MOCK'


def test_cross_origin_websocket_denied(tmp_path):
    with TestClient(create_app(db_path=tmp_path / 'origin.db')) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/api/ws/state', headers={'origin': 'http://untrusted.example'}):
                pass


def test_realtime_subscribers_are_bounded():
    service = SystemStateService(MockProvider())
    queues = [service.subscribe() for _ in range(8)]
    assert all(q.maxsize == 1 for q in queues)
    assert service.subscribe() is None
    service.unsubscribe(queues[0])
    assert service.subscribe() is not None
