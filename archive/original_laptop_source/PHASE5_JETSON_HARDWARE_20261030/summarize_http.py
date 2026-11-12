"""Analyze captured HTTP bytes, preserving absence and provenance; no network."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = ROOT / 'http_lan_20261030'
receipt = json.loads((D / 'result.json').read_text(encoding='utf-8'))
for row in receipt['requests']:
    body = (D / row['body_file']).read_bytes()
    assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']


def load(name):
    return json.loads((D / name).read_text(encoding='utf-8'))


first, second = load('03.body'), load('12.body')
state = load('02.body')
result = {
    'source': 'ACTUAL_LAN_HTTP_CAPTURE_NOT_AUTHENTICATED_HOST_SHELL',
    'client_first_utc': receipt['requests'][0]['timestamp_utc'],
    'client_last_utc': receipt['requests'][-1]['timestamp_utc'],
    'HTTP_receipt_hashes': 'VERIFIED_PASS',
    'readiness': load('01.body'),
    'system_state_except_ultrasonic': {k: v for k, v in state.items() if k != 'ultrasonic'},
    'ultrasonic': state['ultrasonic'],
    'hx711': load('04.body'),
    'bridge': {k: first.get(k) for k in ('health', 'serial_connected', 'device', 'usb_vid', 'usb_pid',
        'usb_serial', 'host_boot_id', 'last_received_at', 'last_rx_monotonic_ms', 'telemetry',
        'telemetry_usable_now', 'bridge_heartbeat_age_seconds', 'actuator_execution', 'serial_tx_enabled')},
    'counter_delta': {k: second['counters'][k] - value for k, value in first['counters'].items()},
    'monotonic_progress_ms': second['updated_monotonic_ms'] - first['updated_monotonic_ms'],
    'owner_verification_historical_not_live_proof': first.get('owner_verification'),
    'endpoint_status': {row['url']: row['http_status'] for row in receipt['requests']},
    'physical_pass': False,
}
with (ROOT / 'HTTP_ANALYSIS.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
    f.write('\n')
print(json.dumps(result, indent=2, ensure_ascii=False))
