"""Verify this session's evidence/owner upload identities and record a NEW receipt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
reports = ('CURRENT_PROGRESS.md', 'JETSON_PREFLIGHT.md', 'ARM64_HARDENING_RESULT.md',
           'SENSOR_REAL_TEST.md', 'SERVO_TEST.md', 'PUMP_TEST.md',
           'WEB_AI_INTEGRATION.md', 'SAFETY_GO_NO_GO.md', 'NEXT_USER_ACTIONS.md')
report_hashes = {}
for name in reports:
    p = ROOT / name
    assert p.stat().st_size > 0 and p.read_text(encoding='utf-8').endswith('\n')
    report_hashes[name] = digest(p)
commands = {}
for p in sorted((ROOT / 'evidence').glob('*/command.json')):
    meta = json.loads(p.read_text(encoding='utf-8'))
    assert digest(p.parent / 'output.log') == meta['output_sha256'], str(p)
    if meta.get('stdin_file'):
        assert digest(Path(meta['stdin_file'])) == meta['stdin_sha256']
    commands[p.parent.name] = {'started_utc': meta['started_utc'], 'exit_code': meta['exit_code'],
                               'command_receipt': str(p), 'output_sha256': meta['output_sha256']}
assert commands['jetson_preflight']['exit_code'] == 255
for name in ('local_package', 'direct_http', 'http_analysis', 'handoff_tool_guards',
             'sealed_native_plan_local', 'bridge_events', 'handoff_checksums'):
    assert commands[name]['exit_code'] == 0
http = ROOT / 'http_lan_20261030'
meta = json.loads((http / 'result.json').read_text())
assert len(meta['requests']) == 14
for row in meta['requests']:
    assert digest(http / row['body_file']) == row['sha256']
sources = {
    'R2_HARDENING_SOURCE.zip': ROOT.parent / 'CANDIDATE_R2_OFFLINE_HARDENING_20261030/R2_HARDENING_SOURCE.zip',
    'safe_release.py': ROOT.parent / 'CANDIDATE_R2_OFFLINE_HARDENING_20261030/tools/safe_release.py',
}
for line in (ROOT / 'HANDOFF_SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert digest(sources.get(name, ROOT / name)) == expected, name
result = {'created_utc': datetime.now(timezone.utc).isoformat(),
          'receipt_integrity': 'VERIFIED_PASS', 'phase5': 'PARTIAL',
          'ARM64_NATIVE_TEST_PASS': 'NOT_RUN', 'SSH': 'BLOCKED_AUTH_EXIT_255',
          'live_telemetry_integration': 'FAIL_UNSUPPORTED_FIRMWARE_MODE_NO_VALID_REPORTS',
          'APP_FLASH': 'NO_GO', 'SERVO_PUMP': 'LOCKED', 'MANUAL_BUZZER': 'DISABLED',
          'production_mutations_issued': False, 'old_Windows_suites_rerun': 0,
          'report_sha256': report_hashes, 'commands': commands,
          'HTTP_capture_receipt_sha256': digest(http / 'result.json'),
          'HTTP_analysis_sha256': digest(ROOT / 'HTTP_ANALYSIS.json'),
          'Bridge_events_sha256': digest(ROOT / 'BRIDGE_EVENTS.json'),
          'handoff_checksums_sha256': digest(ROOT / 'HANDOFF_SHA256SUMS')}
with (ROOT / 'SESSION_RECEIPT.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2); f.write('\n')
print(json.dumps({'receipt_integrity': result['receipt_integrity'], 'reports_verified': len(report_hashes),
                  'command_receipts_verified': len(commands), 'HTTP_bodies_verified': len(meta['requests']),
                  'upload_file_hashes': 'MATCH', 'phase5': 'PARTIAL',
                  'ARM64_NATIVE_TEST_PASS': 'NOT_RUN', 'SSH': 'BLOCKED_AUTH_EXIT_255'}, indent=2))
