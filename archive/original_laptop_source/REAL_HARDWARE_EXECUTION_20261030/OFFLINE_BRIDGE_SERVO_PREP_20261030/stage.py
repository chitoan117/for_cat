"""Create NEW offline Bridge workspace and fixtures from existing logs; no device IO."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[1]
BASE = WS / 'CANDIDATE_R2_OFFLINE_HARDENING_20261030/candidate/bridge'
FW = ROOT.parent / 'INTEGRATED_MANUAL_CANDIDATE'
bridge = ROOT / 'bridge'
bridge.mkdir()
records = {}
for p in BASE.iterdir():
    if p.is_file() and p.suffix in ('.cpp', '.h'):
        shutil.copyfile(p, bridge / p.name)
        records[p.name] = {'source': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
reference = ROOT / 'production_reference'
reference.mkdir()
prod = WS / 'PRODUCTION_INTEGRATION_20261029/release_candidate_v2/payload/jetson/device'
for name in ('telemetry.h', 'esp32_bridge.cpp'):
    shutil.copyfile(prod / name, reference / name)
    records['production_reference/' + name] = {'source': str(prod / name), 'sha256': hashlib.sha256((prod / name).read_bytes()).hexdigest()}
fixtures = ROOT / 'fixtures'
fixtures.mkdir()
frames = []
for p in sorted((FW / 'verification_tx_atomic').glob('*.serial.log')):
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('{'):
            value = json.loads(line)
            if value.get('mode') == 'diag_manual_station':
                frames.append({'source': 'SIMULATED_GPIO_EXISTING_LOG_NOT_REAL_HARDWARE',
                               'origin': str(p), 'payload': value})
assert len(frames) == 37
(fixtures / 'manual_frames.json').write_text(json.dumps(frames, indent=2) + '\n')
for line in (WS / 'CANDIDATE_R2_OFFLINE_HARDENING_20261030/fixtures/r1_quad_reports.log').read_text().splitlines():
    if line.startswith('{'):
        value = json.loads(line)
        if value.get('mode') == 'diag_current_hardware' and value.get('kit_profile') == 'diag_four_ultrasonic':
            (fixtures / 'quad_legacy.json').write_text(json.dumps(value) + '\n')
            break
else:
    raise ValueError('no qualified quad fixture')
(ROOT / 'BASELINE.json').write_text(json.dumps({'base': 'SEALED_R2_OFFLINE_HARDENING_PM5', 'inputs': records,
    'locked_firmware_sha256': '77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93',
    'production_binary_identity': 'NOT_REINSPECTED_OFFLINE_ONLY'}, indent=2) + '\n')
print(json.dumps({'workspace': str(ROOT), 'copied_source_files': len(records), 'existing_simulated_frames': len(frames), 'devices_opened': False}))
