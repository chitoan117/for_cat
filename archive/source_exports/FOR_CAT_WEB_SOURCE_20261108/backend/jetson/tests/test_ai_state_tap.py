import json
from pathlib import Path
import sqlite3
import subprocess
import time
from contextlib import closing

from app.ai_state import AiStateReader

ROOT = Path(__file__).resolve().parents[2]


def test_cpp_tap_consumes_existing_detector_contract_only(tmp_path):
    db = tmp_path / 'synthetic_ai.db'
    process = subprocess.Popen([str(ROOT / '.native-build/esp32/ai_state_tap'), str(db)], stdin=subprocess.PIPE)
    def latest():
        try:
            with closing(sqlite3.connect(db, timeout=.2)) as connection:
                return json.loads(connection.execute('SELECT body FROM ai_latest').fetchone()[0])
        except (sqlite3.Error, TypeError):
            return {}
    def until(classification):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = latest()
            if state.get('classification') == classification:
                return state
            time.sleep(.03)
        raise AssertionError('tap update timed out')
    def send(line):
        process.stdin.write((line + '\n').encode())
        process.stdin.flush()
    try:
        until('UNKNOWN')
        send('DETECTIONS CAT=0.91 MODE=latest PROCESSED=30')
        time.sleep(.1)
        assert latest()['classification'] == 'UNKNOWN'
        send('ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16; monitoring only; no actuator path')
        send('DETECTIONS CAT=0.91 MODE=latest PROCESSED=30')
        assert until('CAT')['confidence'] == .91
        assert AiStateReader(db).status()['classification'] == 'CAT'
        # A bounded cache-write lock must not terminate the stdout consumer or
        # orphan the working detector (a real Nano SD/SQLite contention defect).
        with closing(sqlite3.connect(db)) as locked:
            locked.execute('BEGIN IMMEDIATE')
            send('NONE MODE=latest PROCESSED=45')
            time.sleep(.4)
            assert process.poll() is None
            locked.rollback()
        send('DETECTIONS CAT=0.95 DOG=0.80 MODE=latest PROCESSED=60')
        assert until('DOG')['actuator_execution'] is False
        send('NONE MODE=latest PROCESSED=90')
        assert until('NONE')['confidence'] is None
        process.stdin.close()
        process.wait(timeout=3)
        assert latest()['classification'] == 'UNKNOWN'
        assert AiStateReader(db).status()['health'] == 'DISCONNECTED'
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)


def test_ai_staleness_never_falls_back_to_none(tmp_path):
    db = tmp_path / 'old.db'
    with closing(sqlite3.connect(db)) as connection:
        connection.execute('CREATE TABLE ai_latest(id INTEGER PRIMARY KEY,body TEXT)')
        connection.execute('INSERT INTO ai_latest VALUES(1,?)', (json.dumps({
            'classification': 'CAT', 'health': 'ONLINE', 'confidence': .9,
            'actuator_execution': False, 'host_boot_id': 'fixture', 'updated_monotonic_ms': 1000}),))
        connection.commit()
    result = AiStateReader(db, monotonic=lambda: 10, boot_id='fixture').status()
    assert result['classification'] == 'UNKNOWN' and result['health'] == 'STALE'
