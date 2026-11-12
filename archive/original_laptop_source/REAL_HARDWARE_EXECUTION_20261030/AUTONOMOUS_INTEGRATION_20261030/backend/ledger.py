"""Durable at-most-once sandbox requests; final/history/event in one SQLite commit."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

POLICY = dict(target_grams=35, tolerance_grams=5, minimum_accepted_grams=30,
              maximum_accepted_grams=40, inclusive_bounds=True, control_cutoff_grams=35)


def utc():
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path):
        self.path = Path(path).resolve()
        # New writer cannot accidentally be pointed at canonical production data.
        if not any(p.name == 'sandbox' for p in self.path.parents):
            raise ValueError('explicit offline sandbox path required')
        self.db = sqlite3.connect(self.path, timeout=.08, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS cl_requests(id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('MOCK','REAL')), boot INTEGER, origin INTEGER, calibration INTEGER,
            state TEXT NOT NULL, created_at TEXT NOT NULL, result TEXT, progress TEXT);
          CREATE TABLE IF NOT EXISTS cl_history(id INTEGER PRIMARY KEY, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS cl_events(seq INTEGER PRIMARY KEY, request_id INTEGER, kind TEXT, body TEXT);
          CREATE TABLE IF NOT EXISTS cl_meta(key TEXT PRIMARY KEY, body TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def meta(self, key):
        row = self.db.execute('SELECT body FROM cl_meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_meta(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO cl_meta VALUES(?,?)', (key, json.dumps(value, allow_nan=False)))

    def claim(self, key, source, boot, session, highwater=0, calibration=0):
        if source != 'MOCK':
            raise ValueError('REAL writer unavailable until a qualified sole-owner hardware adapter is supplied')
        if not isinstance(key, str) or not 1 <= len(key) <= 96:
            raise ValueError('bounded durable idempotency key required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT id,boot,origin FROM cl_requests WHERE key=?', (key,)).fetchone()
            if row:
                self.db.commit(); return row[0], False
            if self.db.execute("SELECT 1 FROM cl_requests WHERE state IN ('SENT','PENDING','UNKNOWN_OUTCOME')").fetchone():
                raise ValueError('unresolved request: never auto-resend/re-feed after restart')
            last = self.db.execute('SELECT COALESCE(MAX(id),0) FROM cl_requests').fetchone()[0]
            request_id = max(last, highwater) + 1
            if request_id > 0xffffff:
                raise OverflowError('MCU24-bit ID budget exhausted')
            self.db.execute('INSERT INTO cl_requests VALUES(?,?,?,?,?,?,?,?,NULL,NULL)',
                            (request_id, key, source, boot, session, calibration, 'SENT', utc()))
            self.db.execute('INSERT INTO cl_events(request_id,kind,body) VALUES(?,?,?)',
                            (request_id, 'REQUEST_RESERVED_BEFORE_TX', '{}'))
            self.db.commit(); return request_id, True
        except BaseException:
            self.db.rollback(); raise

    def pending(self, request_id):
        with self.db:
            self.db.execute("UPDATE cl_requests SET state='PENDING' WHERE id=? AND state='SENT'", (request_id,))

    def progress(self, value):
        row = self.db.execute('SELECT source,boot,origin,result FROM cl_requests WHERE id=?', (value['request_id'],)).fetchone()
        if not row or (row[1],row[2]) != (value['boot'],value['origin_session']) or value['final_status_received']:
            raise ValueError('progress request/origin mismatch')
        if row[3] is not None:
            return  # late progress cannot resurrect a committed terminal result
        body = dict(value, source=row[0], actual_dispensed_grams=None, mass_in_band=None,
                    mass_policy=dict(POLICY), measurement_source='NOT_AVAILABLE', physical_validation='NOT_VERIFIED')
        with self.db:
            self.db.execute('UPDATE cl_requests SET progress=? WHERE id=? AND result IS NULL',
                            (json.dumps(body,allow_nan=False),value['request_id']))

    def unknown(self, request_id, reason):
        with self.db:
            row = self.db.execute('SELECT state FROM cl_requests WHERE id=?', (request_id,)).fetchone()
            if row and row[0] in ('SENT', 'PENDING'):
                self.db.execute("UPDATE cl_requests SET state='UNKNOWN_OUTCOME' WHERE id=?", (request_id,))
                self.db.execute('INSERT INTO cl_events(request_id,kind,body) VALUES(?,?,?)',
                                (request_id, 'UNKNOWN_OUTCOME_NO_RESEND', json.dumps({'reason': reason})))

    def reject(self, request_id, reason):
        with self.db:
            self.db.execute("UPDATE cl_requests SET state='REJECTED' WHERE id=? AND state IN ('SENT','PENDING')", (request_id,))
            self.db.execute('INSERT INTO cl_events(request_id,kind,body) VALUES(?,?,?)',
                            (request_id, 'REQUEST_REJECTED_NOT_A_FEED', json.dumps({'reason': reason})))

    def finish(self, result):
        request_id = result['request_id']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT source,boot,origin,state,result,calibration FROM cl_requests WHERE id=?', (request_id,)).fetchone()
            if not row or (row[1], row[2]) != (result['boot'], result['origin_session']):
                raise ValueError('terminal request/boot/origin mismatch')
            if row[3] == 'REJECTED' or (result['calibration_valid'] and row[5] != result['calibration_id']):
                raise ValueError('rejected transaction or calibration mismatch')
            value = {k: v for k, v in result.items() if k not in ('session', 'sequence')}
            value.update(source=row[0], physical_validation='NOT_VERIFIED', mass_policy=dict(POLICY),
                         measurement_source='MOCK_SENSOR' if result['actual_dispensed_grams'] is not None else 'NOT_AVAILABLE')
            actual = value['actual_dispensed_grams']
            value['mass_in_band'] = 30 <= actual <= 40 if actual is not None else None
            # A validated final (not an ACK) can reconcile an unknown outcome.
            # An already-committed conflicting final is still immutable below.
            value['reconciled_from_unknown'] = row[3] == 'UNKNOWN_OUTCOME' or bool(row[4] and json.loads(row[4]).get('reconciled_from_unknown'))
            body = json.dumps(value, sort_keys=True, allow_nan=False)
            if row[4] is not None:
                if row[4] != body:
                    raise ValueError('conflicting terminal replay; original retained')
                self.db.commit(); return False
            self.db.execute('UPDATE cl_requests SET state=?,result=? WHERE id=?', (value['state'], body, request_id))
            self.db.execute('INSERT INTO cl_history VALUES(?,?)', (request_id, body))
            self.db.execute('INSERT INTO cl_events(request_id,kind,body) VALUES(?,?,?)', (request_id, 'FINAL_FEED_STATUS', body))
            self.db.commit(); return True
        except BaseException:
            self.db.rollback(); raise

    def get(self, request_id):
        row = self.db.execute('SELECT id,source,state,created_at,result,progress FROM cl_requests WHERE id=?', (request_id,)).fetchone()
        if not row:
            return None
        if row[4] is not None:
            return {**json.loads(row[4]), 'created_at': row[3]}
        if row[5] is not None:
            return {**json.loads(row[5]), 'state':row[2], 'created_at':row[3]}
        return dict(request_id=row[0], source=row[1], state=row[2], created_at=row[3],
                    mass_policy=dict(POLICY), actual_dispensed_grams=None, latest_observed_grams=None,
                    measurement_source='NOT_AVAILABLE', mass_in_band=None, final_status_received=False,
                    physical_validation='NOT_VERIFIED')

    def readonly(self, kind='requests', limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('bounded limit')
        with sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=.08) as db:
            if kind == 'history':
                return [json.loads(r[0]) for r in db.execute('SELECT body FROM cl_history ORDER BY id DESC LIMIT ?', (limit,))]
            if kind == 'events':
                return [dict(seq=r[0], request_id=r[1], kind=r[2], details=json.loads(r[3]))
                        for r in db.execute('SELECT seq,request_id,kind,body FROM cl_events ORDER BY seq DESC LIMIT ?', (limit,))]
            rows = db.execute('SELECT id,source,state,created_at,result,progress FROM cl_requests ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [json.loads(r[4]) if r[4] else {**json.loads(r[5]), 'state':r[2], 'created_at':r[3]} if r[5] else dict(request_id=r[0], source=r[1], state=r[2], created_at=r[3],
                mass_policy=dict(POLICY), actual_dispensed_grams=None, latest_observed_grams=None,
                measurement_source='NOT_AVAILABLE', mass_in_band=None, final_status_received=False,
                physical_validation='NOT_VERIFIED') for r in rows]
