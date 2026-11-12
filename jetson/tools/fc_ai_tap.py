#!/usr/bin/env python3
"""Resilient AI stdout tap for cat_dog_trt -> SQLite ai_latest."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import re
import sqlite3
import sys
import time

DETECTION_RE = re.compile(r'(CAT|DOG)=([0-9]+(?:\.[0-9]+)?)')


def read_boot_id() -> str:
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    except OSError:
        return 'unknown-boot-id'


def main():
    if len(sys.argv) != 2:
        print('Usage: fc_ai_tap.py <db_path>', file=sys.stderr)
        sys.exit(2)
    db_path = Path(sys.argv[1]).resolve()
    boot_id = read_boot_id()
    storage_errors = 0

    with closing(sqlite3.connect(db_path, timeout=5.0)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute(
            'CREATE TABLE IF NOT EXISTS ai_latest('
            'id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)'
        )
        db.commit()

    def save(health: str, classification: str, confidence: float | None):
        nonlocal storage_errors
        now_ms = int(time.monotonic() * 1000)
        iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        state = {
            'health': health,
            'classification': classification,
            'confidence': round(float(confidence), 4) if confidence is not None else None,
            'source': 'EXISTING_CPP_TENSORRT_STDOUT',
            'host_boot_id': boot_id,
            'updated_monotonic_ms': now_ms,
            'last_observation_at': iso,
            'actuator_execution': False,
            'storage_errors': storage_errors,
        }
        body = json.dumps(state, separators=(',', ':'))
        try:
            with closing(sqlite3.connect(db_path, timeout=3.0)) as conn:
                conn.execute('INSERT OR REPLACE INTO ai_latest VALUES(1, ?)', (body,))
                conn.commit()
        except sqlite3.Error as exc:
            storage_errors += 1
            if storage_errors <= 5 or storage_errors % 100 == 0:
                print(f'AI_STATE_STORAGE {exc}', file=sys.stderr, flush=True)

    save('DISCONNECTED', 'UNKNOWN', None)
    contract = False
    last_printed_cls = None

    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16;'):
                contract = True
                print(f'[ai-tap] {line}', flush=True)
                continue
            if not contract or ' MODE=' not in line or ' PROCESSED=' not in line:
                continue
            if line.startswith('NONE MODE='):
                save('ONLINE', 'NONE', None)
                last_printed_cls = 'NONE'
                continue
            if not line.startswith('DETECTIONS '):
                continue

            classification = 'UNKNOWN'
            confidence = 0.0
            valid = True
            for match in DETECTION_RE.finditer(line):
                species = match.group(1)
                score = float(match.group(2))
                if not math.isfinite(score) or score < 0.0 or score > 1.0:
                    valid = False
                    break
                if (
                    species == 'DOG'
                    or classification == 'UNKNOWN'
                    or (classification == species and score > confidence)
                ):
                    classification = species
                    confidence = score

            if valid and classification != 'UNKNOWN':
                save('ONLINE', classification, confidence)
                if classification != last_printed_cls:
                    print(f'[ai-tap] DETECTED {classification} (conf={confidence:.2f})', flush=True)
                    last_printed_cls = classification
    finally:
        save('DISCONNECTED', 'UNKNOWN', None)


if __name__ == '__main__':
    main()
