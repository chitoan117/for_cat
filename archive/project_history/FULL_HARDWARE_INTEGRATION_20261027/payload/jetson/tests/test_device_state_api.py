import json
import sqlite3
import time
from contextlib import closing

from fastapi.testclient import TestClient
import pytest

from app.device_state import Esp32StateReader
from app.main import create_app
from app import device_state


@pytest.fixture(autouse=True)
def synthetic_identity_for_non_linux_api_fixtures(monkeypatch):
    if device_state.read_host_boot_id() is None:
        monkeypatch.setattr(device_state, 'read_host_boot_id', lambda: 'synthetic-offline-boot')
        monkeypatch.setattr('app.ai_state.read_host_boot_id', lambda: 'synthetic-offline-boot')


def state_db(path, **changes):
    data = {'health': 'ESP32_CONNECTED', 'serial_connected': True,
            'host_boot_id': 'fixture-boot', 'updated_monotonic_ms': 100000,
            'actuator_execution': False, 'serial_tx_enabled': False,
            'time_valid': True, 'telemetry': {'sensors': {'hx711': {'grams': None}}}}
    data.update(changes)
    with closing(sqlite3.connect(str(path))) as db:
        db.execute('CREATE TABLE IF NOT EXISTS esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
        db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)', (json.dumps(data),))
        db.commit()


@pytest.mark.parametrize('now,boot,health,usable', [
    (100, 'fixture-boot', 'ESP32_CONNECTED', True),
    (104, 'fixture-boot', 'ESP32_STALE', False),
    (99, 'fixture-boot', 'ESP32_DISCONNECTED', False),
    (100, 'different-boot', 'ESP32_DISCONNECTED', False),
])
def test_reader_monotonic_freshness_boot_identity(tmp_path, now, boot, health, usable):
    path = tmp_path / 'state.db'
    state_db(path)
    state = Esp32StateReader(path, monotonic=lambda: now, boot_id=boot).status()
    assert state['health'] == health and state['telemetry_usable_now'] is usable
    if not usable:
        assert state['time_valid'] is False


def test_reader_missing_database_never_creates_it(tmp_path):
    path = tmp_path / 'missing.db'
    state = Esp32StateReader(path, boot_id='fixture').status()
    assert state['health'] == 'ESP32_DISCONNECTED' and not path.exists()


@pytest.mark.parametrize('changes', [
    {'actuator_execution': True}, {'serial_tx_enabled': True},
    {'health': 'INVENTED'}, {'updated_monotonic_ms': 'invalid'},
    {'updated_monotonic_ms': float('nan')},
    {'serial_connected': False}, {'telemetry': None}, {'time_valid': 'yes'},
])
def test_reader_invalid_snapshot_fails_closed(tmp_path, changes):
    path = tmp_path / 'state.db'
    state_db(path, **changes)
    state = Esp32StateReader(path, boot_id='fixture-boot').status()
    assert state['health'] == 'ESP32_DISCONNECTED'
    assert state['actuator_execution'] is False


def test_existing_backend_consumes_bridge_without_serial_or_fake_feeds(tmp_path, monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED', '1')
    db = tmp_path / 'one-canonical.db'
    state_db(db, host_boot_id=device_state.read_host_boot_id(),
             updated_monotonic_ms=time.monotonic() * 1000)
    app = create_app(db_path=db)
    # If /status regresses to binary transport polling, fail this test immediately.
    app.state.feeds.status = lambda: (_ for _ in ()).throw(AssertionError('binary status called'))
    with TestClient(app) as client:
        status = client.get('/api/v1/status').json()
        assert status['esp32_online'] is True and status['esp32'] == 'ONLINE'
        assert status['esp32_telemetry']['telemetry']['sensors']['hx711']['grams'] is None
        assert client.get('/api/v1/esp32/status').json()['feed_target_grams'] == 35
        result = client.post('/api/v1/feed/manual')
        assert result.status_code == 503 and 'UNATTENDED_SAFE_MODE' in result.text
        assert client.get('/api/v1/sessions/feeding').json() == []
    with closing(sqlite3.connect(str(db))) as connection:
        assert connection.execute('SELECT COUNT(*) FROM feed_requests').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0


def test_unconfigured_bridge_endpoint_does_not_claim_connected(tmp_path, monkeypatch):
    monkeypatch.delenv('ESP32_BRIDGE_ENABLED', raising=False)
    with TestClient(create_app(db_path=tmp_path / 'normal.db')) as client:
        assert client.get('/api/v1/esp32/status').status_code == 503


def test_bridge_mode_refuses_competing_binary_serial(tmp_path, monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED', '1')
    monkeypatch.setenv('ESP32_TRANSPORT', 'SERIAL')
    monkeypatch.setenv('ESP32_SERIAL_DEVICE', '/dev/DO_NOT_OPEN')
    with pytest.raises(ValueError, match='owns serial'):
        create_app(db_path=tmp_path / 'blocked.db')
