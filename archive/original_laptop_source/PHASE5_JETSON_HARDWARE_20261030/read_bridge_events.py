"""Single GET of existing bounded Bridge event log via audited read-only route."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import build_opener, ProxyHandler, Request
from http_readonly_audit import NoRedirect

ROOT = Path(__file__).resolve().parent
url = 'http://192.168.123.8:8000/api/v1/esp32/events?limit=20'
timestamp = datetime.now(timezone.utc).isoformat()
with build_opener(ProxyHandler({}), NoRedirect()).open(Request(url, method='GET'), timeout=8) as response:
    raw = response.read(1024 * 1024 + 1)
    if response.status != 200 or len(raw) > 1024 * 1024:
        raise ValueError('read-only event response unavailable/budget exceeded')
with (ROOT / 'BRIDGE_EVENTS.json').open('xb') as f:
    f.write(raw)
events = json.loads(raw)
print(json.dumps({'timestamp_utc': timestamp, 'source': 'ACTUAL_LAN_HTTP_GET', 'command': 'GET ' + url,
                  'http_status': 200, 'events': events}, indent=2, ensure_ascii=False))
