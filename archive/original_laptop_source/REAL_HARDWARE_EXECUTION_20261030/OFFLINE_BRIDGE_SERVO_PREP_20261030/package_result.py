"""Record new patch/evidence integrity only. No rebuild/tests/remote/device access."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = json.loads((ROOT/'BASELINE.json').read_text())
for entry in base['inputs'].values():
    assert sha(Path(entry['source'])) == entry['sha256'], entry['source']
candidate = ROOT.parent/'INTEGRATED_MANUAL_CANDIDATE'
image = candidate/'build_safe_txatomic/artifacts/firmware.bin'
assert image.stat().st_size == 415456 and sha(image) == base['locked_firmware_sha256']
patch = []; changes = []
for p in sorted((ROOT/'bridge').iterdir()):
    if p.suffix not in ('.h', '.cpp'):
        continue
    entry = base['inputs'].get(p.name)
    before = Path(entry['source']).read_text(encoding='utf-8') if entry else ''
    after = p.read_text(encoding='utf-8')
    if before != after:
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                     fromfile='a/bridge/'+p.name if entry else '/dev/null', tofile='b/bridge/'+p.name))
        changes.append({'path': 'bridge/'+p.name, 'before_sha256': entry['sha256'] if entry else None, 'after_sha256': sha(p)})
with (ROOT/'SOURCE_CHANGES.patch').open('x', encoding='utf-8', newline='\n') as f:
    f.write(''.join(patch))
test = json.loads((ROOT/'bridge_tests_initial/result.json').read_text())
text = (ROOT/'bridge_tests_initial/tests.log').read_text()
assert test['status'] == 'SIMULATION_PASS' and re.search(r'16 passed\b', text)
reports = ('SERVO_TEST_READY.md', 'BRIDGE_COMPATIBILITY.md', 'MAINTENANCE_GATE.md', 'NEXT_PHYSICAL_STEP.md')
for name in reports:
    assert (ROOT/name).stat().st_size > 0
files = {}
for p in ROOT.rglob('*'):
    if p.is_file() and p.suffix not in ('.exe', '.pdb', '.pyc') and p.name!='RESULT.json':
        files[p.relative_to(ROOT).as_posix()] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'NEW_OFFLINE_BRIDGE_AND_SERVO_HANDOFF',
          'bridge_tests': 'SIMULATION_PASS', 'new_pytest_cases': 16, 'retained_simulated_frames': 37,
          'whole_POSIX_Bridge_build': 'NOT_RUN', 'Jetson_ESP32_runtime': 'NOT_RUN',
          'firmware_rebuilt': False, 'old_30_firmware_regressions_rerun': False,
          'locked_firmware_sha256': sha(image), 'pump_motor_load_isolation': 'OWNER_CONFIRMED_TWO_OUTPUT_WIRES_REMOVED',
          'APP_FLASH': 'NO_GO', 'physical_servo_test': 'BLOCKED_PENDING_GATES_AND_APPROVAL',
          'production_changed': False, 'serial_opened': False, 'services_changed': False,
          'AI_closed_loop_dispatcher': 'DEFERRED_SERVO_FIRST_NO_AUTO_CAPABILITY_IN_MANUAL_FIRMWARE',
          'patch_base': base['base'], 'changes': changes, 'files': dict(sorted(files.items()))}
with (ROOT/'RESULT.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2); f.write('\n')
print(json.dumps({k: result[k] for k in ('bridge_tests','new_pytest_cases','locked_firmware_sha256',
      'firmware_rebuilt','old_30_firmware_regressions_rerun','pump_motor_load_isolation','APP_FLASH')}, indent=2))
