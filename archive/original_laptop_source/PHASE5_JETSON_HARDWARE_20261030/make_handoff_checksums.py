"""Checksum NEW owner handoff files and existing image identities; no sealing/rebuild."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
C = ROOT.parent / 'CANDIDATE_R2_OFFLINE_HARDENING_20261030'
KIT = ROOT.parent / 'HARDWARE_PHYSICAL_BRINGUP_20261029'
sources = {
    'R2_HARDENING_SOURCE.zip': C / 'R2_HARDENING_SOURCE.zip',
    'safe_release.py': C / 'tools/safe_release.py',
    'owner_arm64.py': ROOT / 'owner_arm64.py',
    'jetson_preflight.sh': ROOT / 'jetson_preflight.sh',
    'http_readonly_audit.py': ROOT / 'http_readonly_audit.py',
}
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
identities = {}
for label, path, size, expected in (
    ('sensor_image', KIT / 'artifacts/diag_four_ultrasonic/firmware.bin', 400304,
     'a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56'),
    ('rollback_app', KIT / 'web_hardware/rollback_original_app_00010000.bin', 381984,
     '820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826'),
):
    actual = digest(path)
    assert path.stat().st_size == size and actual == expected
    identities[label] = {'path': str(path), 'bytes': size, 'sha256': actual, 'status': 'VERIFIED_PASS_LOCAL_BYTES_ONLY'}
entries = {name: digest(path) for name, path in sources.items()}
with (ROOT / 'HANDOFF_SHA256SUMS').open('xb') as f:
    f.write(''.join(value + '  ' + name + '\n' for name, value in sorted(entries.items())).encode('ascii'))
with (ROOT / 'HANDOFF_IDENTITIES.json').open('x', encoding='utf-8') as f:
    json.dump({'handoff': entries, 'local_hardware_artifacts': identities, 'device_access': False}, f, indent=2)
    f.write('\n')
print(json.dumps({'handoff': entries, 'local_hardware_artifacts': identities, 'device_access': False}, indent=2))
