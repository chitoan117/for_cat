"""Passive state consumer; never runs Python inference or opens the camera."""
from contextlib import closing
from pathlib import Path
import sqlite3
import time
import math
from app.device_state import decode_cached_object, read_host_boot_id


class AiStateReader:
    def __init__(self, db_path, monotonic=time.monotonic, boot_id=None):
        self.path = Path(db_path).resolve()
        self.monotonic = monotonic
        self.boot_id = boot_id if boot_id is not None else read_host_boot_id()

    def status(self):
        unknown = {'classification': 'UNKNOWN', 'confidence': None, 'health': 'DISCONNECTED',
                   'last_observation_at': None, 'source': 'EXISTING_CPP_TENSORRT_STDOUT'}
        try:
            if not self.boot_id:
                return unknown
            with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
                row = db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()
            if not row:
                return unknown
            data = decode_cached_object(row[0], 4096)
            if data.get('classification') not in ('CAT', 'DOG', 'NONE', 'UNKNOWN') or data.get('actuator_execution') is not False:
                return unknown
            if data.get('host_boot_id') != self.boot_id:
                return unknown
            stamp = data.get('updated_monotonic_ms')
            if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
                return unknown
            age = self.monotonic() - stamp / 1000
            if not math.isfinite(age):
                return unknown
            if age < 0 or age > 3:
                unknown['health'] = 'STALE'
                return unknown
            if data.get('health') != 'ONLINE':
                return unknown
            confidence = data.get('confidence')
            if data['classification'] == 'UNKNOWN':
                return unknown
            if data['classification'] in ('CAT', 'DOG') and (
                    type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
                return unknown
            if data['classification'] == 'NONE' and confidence is not None:
                return unknown
            return {key: data.get(key) for key in ('classification', 'confidence', 'health', 'last_observation_at', 'source')}
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return unknown
