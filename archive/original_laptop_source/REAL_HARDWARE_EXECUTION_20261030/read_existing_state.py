"""Capture two existing GET-only endpoints; no serial/camera/service/control API."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request

ROOT = Path(__file__).resolve().parent


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


out = ROOT / ('read_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
out.mkdir(mode=0o700)
receipts = []
opener = build_opener(ProxyHandler({}), NoRedirect())
code = 0
for label, path in (('esp32_status', '/api/v1/esp32/status'), ('bridge_events', '/api/v1/esp32/events?limit=5')):
    url = 'http://192.168.123.8:8000' + path
    row = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'command': 'GET ' + url,
           'source': 'ACTUAL_LAN_HTTP_RESPONSE'}
    try:
        with opener.open(Request(url, method='GET'), timeout=8) as response:
            row['http_status'] = response.status
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('response exceeds audit budget')
        (out / (label + '.json')).write_bytes(raw)
        row.update(exit_code=0, sha256=hashlib.sha256(raw).hexdigest())
        value = json.loads(raw)
        if label == 'esp32_status':
            print(json.dumps({k: value.get(k) for k in ('health', 'serial_connected', 'device', 'usb_serial',
                  'serial_tx_enabled', 'actuator_execution', 'telemetry', 'counters', 'telemetry_usable_now')}, indent=2))
        else:
            print(json.dumps(value, indent=2))
    except Exception as e:
        row.update(exit_code=2, error=type(e).__name__ + ': ' + str(e))
        code = 2
    receipts.append(row)
    if code:
        break
with (out / 'receipt.json').open('x', encoding='utf-8') as f:
    json.dump({'requests': receipts, 'exit_code': code, 'serial_opened': False,
               'service_changes': False, 'actuator_commands_sent': False}, f, indent=2)
    f.write('\n')
print(json.dumps({'evidence': str(out), 'exit_code': code}))
sys.exit(code)
