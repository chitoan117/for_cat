"""Bounded dry-run inbox for the ONE C++ arbiter; never a hardware transport."""
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3


class DryRunRequests:
    def __init__(self, path):
        self.path = Path(path)

    def enqueue(self, request_id, source, sub_source='', target_grams=35):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', request_id) or source not in ('AUTO_CAT', 'SCHEDULED', 'MANUAL'):
            raise ValueError('invalid request identity/source')
        if target_grams != 35 or isinstance(target_grams, bool):
            raise ValueError('canonical target must be 35g')
        if source == 'MANUAL' and sub_source not in ('BUTTON', 'KIOSK', 'APP'):
            raise ValueError('invalid manual sub-source')
        body = {'request_id': request_id, 'source': source, 'sub_source': sub_source,
                'target_grams': 35, 'timestamp': datetime.now(timezone.utc).isoformat(),
                'actuator_execution': False, 'actual_dispensed_grams': None}
        with closing(sqlite3.connect(self.path, timeout=.2)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS feed_dry_run_requests(request_id TEXT PRIMARY KEY,body TEXT NOT NULL,decision TEXT)')
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT body,decision FROM feed_dry_run_requests WHERE request_id=?', (request_id,)).fetchone()
            if old:
                previous = json.loads(old[0])
                if any(previous[k] != body[k] for k in ('source', 'sub_source', 'target_grams')):
                    raise ValueError('request ID payload conflict')
                return {'request': previous, 'decision': json.loads(old[1]) if old[1] else None}
            if db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0] >= 256:
                raise OverflowError('dry-run request ledger full; fail closed')
            db.execute('INSERT INTO feed_dry_run_requests VALUES(?,?,NULL)', (request_id, json.dumps(body)))
            db.commit()
        return {'request': body, 'decision': None}

    def get(self, request_id):
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
            row = db.execute('SELECT body,decision FROM feed_dry_run_requests WHERE request_id=?', (request_id,)).fetchone()
        return {'request': json.loads(row[0]), 'decision': json.loads(row[1]) if row[1] else None} if row else None
