"""Read-only bounded REAL availability sampling; no serial/camera/control access."""
import argparse
import collections
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import tempfile
import time
import urllib.request


def atomic_json(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.watch-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(out, duration, interval):
    out.mkdir(parents=True, exist_ok=False)
    logger = logging.getLogger('forcat-overnight')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(out / 'samples.jsonl', maxBytes=1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    started = time.monotonic()
    counts = collections.Counter()
    classifications = collections.Counter()
    alerts = []
    latest = None
    previous = {}
    timeout_increases = collections.Counter()
    report = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status': 'RUNNING', 'requested_seconds': duration, 'sample_interval_seconds': interval,
              'scope': 'PERIODIC_REAL_AVAILABILITY_NOT_EVERY_SENSOR_PULSE',
              'actuator_commands_sent': False, 'serial_opened': False, 'camera_opened': False}
    print(json.dumps({'status': 'RUNNING', 'output': str(out), 'duration_s': duration}), flush=True)
    next_sample = started
    try:
        while time.monotonic() - started < duration:
            record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=4) as response:
                    state = json.load(response)
                if state.get('data_source') != 'REAL':
                    raise ValueError('canonical REAL provider missing')
                flags = state['safety']
                safe = all(flags.get(k) is False for k in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water', 'actuator_execution')) and flags.get('actuator_outputs_enabled') == 0
                if not safe:
                    counts['unsafe_state_observations'] += 1
                    raise RuntimeError('SAFETY_STATE_VIOLATION')
                latest = state
                record['state'] = state
                counts['api_success'] += 1
                counts['esp32_connected' if state['esp32']['connected'] else 'esp32_unavailable'] += 1
                counts['ai_online' if state['ai']['health'] == 'ONLINE' else 'ai_unavailable'] += 1
                classifications[state['ai']['classification']] += 1
                for role in ('approach', 'water_operational'):
                    sensor = state[role]
                    counts[role + ('_valid_sample' if sensor['valid'] else '_invalid_sample')] += 1
                    counter = sensor['timeout_count']
                    old = previous.get(role)
                    if old is not None:
                        if counter >= old:
                            timeout_increases[role] += counter-old
                        else:
                            counts[role+'_counter_resets'] += 1
                    previous[role] = counter
            except Exception as error:
                counts['api_or_validation_errors'] += 1
                record['error'] = type(error).__name__ + ': ' + str(error)
                if len(alerts) < 50:
                    alerts.append({'utc': record['utc'], 'error': record['error']})
            counts['samples'] += 1
            logger.info(json.dumps(record, separators=(',', ':')))
            report.update(elapsed_seconds=round(time.monotonic()-started, 3), counts=dict(counts),
                          ai_classifications=dict(classifications), firmware_timeout_increases=dict(timeout_increases),
                          alerts=alerts, latest_state=latest)
            atomic_json(out/'SUMMARY.json', report)
            if counts['unsafe_state_observations']:
                report['status'] = 'STOPPED_SAFETY_STATE_VIOLATION'
                break
            next_sample += interval
            time.sleep(max(0, min(next_sample, started+duration)-time.monotonic()))
        else:
            report['status'] = 'COMPLETED'
    except BaseException as error:
        report.update(status='STOPPED_EARLY', stop_reason=type(error).__name__+': '+str(error))
        raise
    finally:
        report['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        atomic_json(out/'SUMMARY.json', report)
        atomic_json(out/'FINAL.json', report)
        handler.close()
        print(json.dumps({'status': report['status'], 'output': str(out)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=8*3600)
    parser.add_argument('--interval', type=float, default=30)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 12*3600 or not .1 <= args.interval <= 300:
        parser.error('bounded duration/interval required')
    run(args.out, args.seconds, args.interval)
