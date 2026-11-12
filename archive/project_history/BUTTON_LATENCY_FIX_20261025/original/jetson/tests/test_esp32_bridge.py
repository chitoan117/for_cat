"""REAL C++ bridge process + Linux PTYs, synthetic data only, no physical serial."""
import copy
import json
import os
from pathlib import Path
import pty
import sqlite3
import subprocess
import time
from contextlib import closing

import pytest

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / '.native-build/esp32/esp32_bridge'
FIXTURE = json.loads((ROOT / 'jetson/tests/fixtures/esp32_current.synthetic.json').read_text())


def wait_for(function, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = function()
        if result:
            return result
        time.sleep(.04)
    raise AssertionError('bounded wait expired')


class Rig:
    def __init__(self, path):
        self.path = path
        self.db = path / 'synthetic.db'
        self.port = path / 'synthetic-port'
        self.master = None
        self.attach()
        self.output = (path / 'execution.log').open('wb')
        self.process = subprocess.Popen([str(BINARY), '--device', str(self.port), '--db', str(self.db),
                                         '--log', str(path / 'bounded.jsonl'), '--reconnect-ms', '100',
                                         '--stale-ms', '1500'], stdout=self.output, stderr=subprocess.STDOUT)
        wait_for(lambda: self.state().get('serial_connected'))

    def attach(self):
        self.master, slave = pty.openpty()
        device = os.ttyname(slave)
        os.close(slave)
        if self.port.is_symlink():
            self.port.unlink()
        self.port.symlink_to(device)
        os.set_blocking(self.master, False)

    def state(self):
        try:
            with closing(sqlite3.connect(str(self.db), timeout=.2)) as db:
                row = db.execute('SELECT body FROM esp32_latest').fetchone()
                return json.loads(row[0]) if row else {}
        except sqlite3.Error:
            return {}

    def send(self, value=None, *, uptime=None, count=None):
        data = copy.deepcopy(FIXTURE) if value is None else copy.deepcopy(value)
        if uptime is not None:
            data['monotonic_ms'] = uptime
        if count is not None:
            current = data['current_hardware']
            current['manual_button_request_count'] = current['button_press_count'] = count
            current['button_last_press_ms'] = data['monotonic_ms'] if count else None
        raw = (json.dumps(data) + '\n').encode()
        for offset in range(0, len(raw), 37):
            os.write(self.master, raw[offset:offset + 37])

    def events(self, kind=None):
        with closing(sqlite3.connect(str(self.db), timeout=.2)) as db:
            rows = db.execute('SELECT kind,body FROM esp32_events ORDER BY seq').fetchall()
        return [json.loads(body) for name, body in rows if kind is None or name == kind]

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.output.close()
        if self.master is not None:
            os.close(self.master)
            self.master = None


@pytest.fixture
def rig(tmp_path):
    instance = Rig(tmp_path)
    try:
        yield instance
    finally:
        instance.close()


def test_split_serial_framing_normalization_and_no_serial_tx(rig):
    rig.send()
    state = wait_for(lambda: rig.state() if rig.state().get('health') == 'ESP32_CONNECTED' else None)
    assert state['actuator_execution'] is False and state['serial_tx_enabled'] is False
    sensors = state['telemetry']['sensors']
    assert sensors['hx711']['grams'] is None
    assert sensors['hx711']['raw_counts'] == -671318
    assert sensors['hx711']['health'] == 'NOT_CALIBRATED'
    assert sensors['approach']['distance_cm'] == 25
    assert sensors['water_operational']['distance_cm'] == 60
    assert sensors['food_reservoir']['percent'] is None
    assert sensors['food_reservoir']['health'] == 'NOT_WIRED'
    with pytest.raises(BlockingIOError):
        os.read(rig.master, 4096)  # daemon never writes a command or terminal echo


def test_malformed_bad_health_then_recovers(rig):
    os.write(rig.master, b'{broken\n')
    wait_for(lambda: rig.state().get('health') == 'ESP32_BAD_TELEMETRY')
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    assert rig.state()['counters']['parse_errors'] == 1


def test_oversized_line_discards_and_recovers(rig):
    os.write(rig.master, b'x' * 5000 + b'\n')
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    assert rig.state()['counters']['oversized_lines'] == 1


def test_stale_is_not_disconnected(rig):
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    wait_for(lambda: rig.state().get('health') == 'ESP32_STALE')
    assert rig.state()['serial_connected'] is True


def test_repeated_uptime_does_not_keep_frozen_device_fresh(rig):
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    for _ in range(8):
        rig.send(uptime=1000)
        time.sleep(.3)
    wait_for(lambda: rig.state().get('health') == 'ESP32_STALE')
    assert rig.state()['counters']['unchanged_uptime_reports'] >= 1


def test_disconnect_reconnect_partial_buffer_cleared(rig):
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    os.write(rig.master, b'{"unfinished":')
    os.close(rig.master)
    rig.master = None
    wait_for(lambda: rig.state().get('health') == 'ESP32_DISCONNECTED')
    rig.attach()
    wait_for(lambda: rig.state().get('serial_connected'))
    rig.send(uptime=2000)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    assert rig.state()['counters']['reconnects'] >= 1
    assert rig.state()['counters']['parse_errors'] == 0


def test_button_counter_dry_run_once_no_feed_records(rig):
    rig.send(count=0)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    rig.send(uptime=2000, count=1)
    event = wait_for(lambda: rig.events('feed_request_dry_run'))[0]
    assert event['source'] == 'MANUAL' and event['manual_source'] == 'BUTTON'
    assert event['reason'] == 'UNATTENDED_SAFE_MODE'
    assert event['qualification_reason'] == 'WEIGHT_NOT_CALIBRATED'
    assert event['target_grams'] == 35 and event['actual_dispensed_grams'] is None
    assert event['actuator_execution'] is False
    for stamp in range(3000, 7000, 1000):
        rig.send(uptime=stamp, count=1)
    time.sleep(.2)
    assert len(rig.events('feed_request_dry_run')) == 1
    rig.send(uptime=8000, count=2)
    wait_for(lambda: len(rig.events('feed_request_dry_run')) == 2)


def test_manual_web_inbox_uses_same_cpp_dry_run_arbiter(rig):
    from app.dry_run_requests import DryRunRequests
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    requests = DryRunRequests(rig.db)
    for sub_source in ('APP', 'KIOSK'):
        requests.enqueue(sub_source, 'MANUAL', sub_source)
    for sub_source in ('APP', 'KIOSK'):
        result = wait_for(lambda: requests.get(sub_source) if requests.get(sub_source)['decision'] else None)
        assert result['decision']['status'] == 'DRY_RUN_BLOCKED'
        assert result['decision']['qualification_reason'] == 'WEIGHT_NOT_CALIBRATED'
        assert result['decision']['target_grams'] == 35
        assert result['decision']['actuator_execution'] is False
    requests.enqueue('APP', 'MANUAL', 'APP')
    time.sleep(.2)
    assert len(rig.events('feed_request_dry_run')) == 2


def test_button_initial_counter_and_offline_gaps_not_replayed(rig):
    rig.send(count=5)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    assert not rig.events('feed_request_dry_run')
    rig.send(uptime=2000, count=8)
    wait_for(lambda: any(e.get('reason') == 'BUTTON_COUNTER_GAP_NOT_REPLAYED' for e in rig.events()))
    assert not rig.events('feed_request_dry_run')


def test_fast_button_event_lines_not_dropped_between_json_reports(rig):
    rig.send(count=0)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    os.write(rig.master, b'MANUAL_BUTTON_FEED_REQUEST count=1 monotonic_ms=1100 actuator_blocked=true\n'
                        b'MANUAL_BUTTON_FEED_REQUEST count=2 monotonic_ms=1300 actuator_blocked=true\n')
    wait_for(lambda: len(rig.events('feed_request_dry_run')) == 2)
    rig.send(uptime=2000, count=2)
    os.write(rig.master, b'MANUAL_BUTTON_FEED_REQUEST count=2 monotonic_ms=1300 actuator_blocked=true\n')
    time.sleep(.2)
    assert len(rig.events('feed_request_dry_run')) == 2


def test_device_reset_does_not_replay_button(rig):
    rig.send(uptime=5000, count=2)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    rig.send(uptime=50, count=0)
    wait_for(lambda: any(e.get('reason') == 'ESP32_UPTIME_RESET' for e in rig.events()))
    assert not rig.events('feed_request_dry_run')
    rig.send(uptime=100, count=1)
    wait_for(lambda: len(rig.events('feed_request_dry_run')) == 1)


@pytest.mark.parametrize('key', ['servo_armed', 'pump_armed', 'auto_feed', 'auto_water'])
def test_unsafe_safety_latches_and_closes_port(rig, key):
    data = copy.deepcopy(FIXTURE)
    data['current_hardware'][key] = True
    rig.send(data)
    wait_for(lambda: rig.state().get('unsafe_telemetry_latched') is True)
    assert rig.state()['health'] == 'ESP32_BAD_TELEMETRY'
    assert rig.state()['serial_connected'] is False
    time.sleep(.3)
    assert rig.state()['counters']['connections'] == 1


def test_second_bridge_cannot_own_same_database(rig):
    result = subprocess.run([str(BINARY), '--db', str(rig.db), '--device', str(rig.port)],
                            capture_output=True, timeout=3)
    assert result.returncode != 0
    assert b'another canonical bridge' in result.stderr


def test_sqlite_writer_contention_does_not_reset_serial(rig):
    with closing(sqlite3.connect(str(rig.db))) as locked:
        locked.execute('BEGIN IMMEDIATE')
        rig.send()
        time.sleep(1)
        assert rig.process.poll() is None
        locked.rollback()
    rig.send(uptime=2000)
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    assert rig.state()['counters']['storage_errors'] >= 1
    assert rig.state()['counters']['connections'] == 1


def test_exit_publishes_disconnected_and_preserves_existing_schema(tmp_path):
    db_path = tmp_path / 'existing.db'
    with closing(sqlite3.connect(str(db_path))) as db:
        db.executescript("CREATE TABLE events(seq INTEGER PRIMARY KEY,kind TEXT,body TEXT);"
                         "INSERT INTO events VALUES(1,'USER','keep'); PRAGMA user_version=2;")
    subprocess.run([str(BINARY), '--device', str(tmp_path / 'absent'), '--db', str(db_path),
                    '--log', str(tmp_path / 'log.jsonl'), '--seconds', '1'], check=True, timeout=5)
    with closing(sqlite3.connect(str(db_path))) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        assert db.execute('SELECT body FROM events').fetchone()[0] == 'keep'
        assert json.loads(db.execute('SELECT body FROM esp32_latest').fetchone()[0])['health'] == 'ESP32_DISCONNECTED'


def test_bounded_database_retention_and_log_rotation(rig):
    # Accelerate pre-existing ring limits without emitting thousands of fake feeds.
    with closing(sqlite3.connect(str(rig.db))) as db:
        db.executemany('INSERT INTO esp32_events(kind,occurred_at,body) VALUES(?,?,?)',
                       [('synthetic', 'test', '{}')] * 1001)
        db.commit()
    log = rig.path / 'bounded.jsonl'
    with log.open('ab') as out:
        out.write(b' ' * (1024 * 1024))
    rig.send()
    wait_for(lambda: rig.state().get('health') == 'ESP32_CONNECTED')
    with closing(sqlite3.connect(str(rig.db))) as db:
        assert db.execute('SELECT COUNT(*) FROM esp32_events').fetchone()[0] <= 1000
    assert (rig.path / 'bounded.jsonl.1').exists()
