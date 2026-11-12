"""Python3.6+ bounded GET-only audit of existing cached APIs; no identity spoofing.

No camera/watch/MJPEG, legacy /api/v1/status, feed polling, POST or DB writes.
Default PLAN; output must be a NEW directory. A denied/unreachable health GET stops.
"""
from __future__ import print_function
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request

PATHS = ('/api/v1/health', '/api/v1/readiness', '/api/status',
         '/api/v1/esp32/status', '/api/hx711/status',
         '/api/v1/feeding-history?limit=5', '/api/v1/drinking-history?limit=5',
         '/api/v1/sessions/feeding?limit=5', '/api/v1/sessions/drinking?limit=5',
         '/api/v1/hardware-diagnostics/status', '/kiosk')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', default='http://127.0.0.1:8000')
    p.add_argument('--execute', choices=('GET_EXISTING_STATUS',))
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    base = a.base.rstrip('/')
    u = urlparse(base)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
        p.error('plain existing API origin required; no credentials/path/query')
    if u.scheme == 'http' and u.hostname not in ('127.0.0.1', 'localhost', '192.168.123.8'):
        p.error('HTTP limited to explicit project LAN/loopback addresses')
    if not a.execute:
        print(json.dumps({'mode': 'PLAN_ONLY', 'base': base, 'paths': PATHS,
                          'camera_opened': False, 'serial_opened': False}))
        return 0
    if not a.out or a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():
        p.error('NEW output directory with existing parent required')
    a.out.mkdir(mode=0o700)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    records = []
    for round_number in range(2):
        paths = PATHS if round_number == 0 else ('/api/status', '/api/v1/esp32/status', '/api/hx711/status')
        if round_number:
            time.sleep(4)  # two cached observations, not a continuous poller
        for path in paths:
            row = {'timestamp_utc': utc(), 'method': 'GET', 'url': base + path,
                   'round': round_number, 'source': 'ACTUAL_HTTP_RESPONSE'}
            start = time.monotonic()
            try:
                try:
                    response = opener.open(Request(base + path, method='GET'), timeout=8)
                except HTTPError as e:
                    response = e
                with response:
                    row['http_status'] = response.code
                    row['content_type'] = response.headers.get('Content-Type')
                    body = response.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise ValueError('response exceeds 1MiB audit budget')
                name = '%02d.body' % len(records)
                (a.out / name).write_bytes(body)
                row.update(body_file=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                row['command_exit_code'] = 0  # HTTP 4xx/5xx kept separately
            except Exception as e:
                row.update(command_exit_code=2, error=type(e).__name__ + ': ' + str(e))
            row['elapsed_seconds'] = round(time.monotonic() - start, 3)
            records.append(row)
            print(json.dumps(row, sort_keys=True))
            if row.get('command_exit_code') or row.get('http_status') in (401, 403) or (path == '/api/v1/health' and row.get('http_status') != 200):
                result = {'status': 'BLOCKED', 'reason': 'HTTP_ACCESS_OR_ENDPOINT_UNAVAILABLE', 'requests': records,
                          'production_runtime_pass': False, 'physical_pass': False}
                (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                return 2
    result = {'status': 'CAPTURED_REQUIRES_REVIEW', 'requests': records,
              'production_runtime_pass': False, 'physical_pass': False}
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
