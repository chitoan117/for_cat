"""Passive state consumer; never runs Python inference or opens the camera."""
from contextlib import closing
from pathlib import Path
import sqlite3
import time
import math
from app.device_state import decode_cached_object, read_host_boot_id
from app.ai_frame_contract import validate as validate_frame


class AiStateReader:
    def __init__(self, db_path, monotonic=time.monotonic, boot_id=None):
        self.path = Path(db_path).resolve()
        self.monotonic = monotonic
        self.boot_id = boot_id if boot_id is not None else read_host_boot_id()

    def status(self):
        unknown = {'classification': 'UNKNOWN', 'confidence': None, 'health': 'DISCONNECTED',
                   'last_observation_at': None, 'source': 'UNKNOWN', 'data_source': 'UNKNOWN',
                   'simulated': None, 'frame_metadata_available': False}
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
            if data.get('data_source') not in (None,'REAL') or data.get('simulated') is True:
                return unknown
            modern = 'ai_schema_version' in data
            if modern and (type(data['ai_schema_version']) is not int or data['ai_schema_version'] != 1):
                return unknown
            provenance = {'source': data.get('source', 'UNKNOWN'),
                          'data_source': data.get('data_source') or ('REAL' if data.get('source') == 'EXISTING_CPP_TENSORRT_STDOUT' else 'UNKNOWN'),
                          'simulated': data.get('simulated'), 'frame_metadata_available': False}
            unknown.update(provenance)
            stamp = data.get('updated_monotonic_ms')
            if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
                return unknown
            age = self.monotonic() - stamp / 1000
            if not math.isfinite(age):
                return unknown
            if age < 0 or age > (1.5 if data.get('ai_schema_version')==1 else 3):
                unknown['health'] = 'STALE'
                return unknown
            if data.get('health') != 'ONLINE':
                return unknown
            if modern:
                validate_frame(data, int(self.monotonic()*1000), self.boot_id)
            confidence = data.get('confidence')
            if data['classification'] == 'UNKNOWN':
                return unknown
            if data['classification'] in ('CAT', 'DOG') and (
                    type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
                return unknown
            if data['classification'] == 'NONE' and confidence is not None:
                return unknown
            return {**{key: data.get(key) for key in ('classification', 'confidence', 'health', 'last_observation_at',
                    'ai_schema_version','producer_epoch','source_frame_id','roi_sequence')}, **provenance,
                    'frame_metadata_available': modern,
                    'captured_monotonic_ms': data.get('roi_observation_ms') if modern else None,
                    'age_seconds': age}
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return unknown
