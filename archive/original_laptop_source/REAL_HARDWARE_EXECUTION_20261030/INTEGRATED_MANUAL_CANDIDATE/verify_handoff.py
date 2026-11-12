"""Check NEW helper refusal paths, immutable build/source identity and record receipt."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
out = ROOT / 'handoff_checks'
out.mkdir()
checks = 0


def check(value):
    global checks
    assert value
    checks += 1


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


commands = []
for name in ('manual_console.py', 'flash_plan.py'):
    ast.parse((ROOT / name).read_text(), feature_version=(3, 6))
    args = [sys.executable, '-B', str(ROOT / name)]
    q = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    (out / (name + '.log')).write_bytes(q.stdout)
    commands.append({'command': args, 'exit_code': q.returncode})
    check(q.returncode == 0)
    result = json.loads(q.stdout)
    check(result['mode'] == 'PLAN_ONLY')
    if name == 'flash_plan.py':
        check(result['write_argv_available'] is False and 'write_argv' not in result)

console = load('manual_console')
for command in ('servo arm YES', 'pump arm YES', 'pump on 100', 'buzzer test CONFIRM', 'hx import 1 2 CONFIRM'):
    check(not console.validate_command(command, {}, {}))
approved = {'allow_servo': True, 'servo_power_mechanics_reviewed': True, 'pump_load_isolated': True,
            'servo_positions_us': [1450, 1550, 1500, 1550]}
check(console.validate_command('servo configure 1450 1550 1500 1550 CONFIRM', approved, {}))
check(not console.validate_command('servo configure 1000 2000 1500 1800 CONFIRM', approved, {}))
check(not console.validate_command('servo set 1600', approved, {}))
pump = {'allow_pump': True, 'pump_power_driver_priming_reviewed': True, 'servo_load_isolated': True,
        'pump_off_level': 0, 'maximum_pump_ms': 100}
check(not console.validate_command('pump on 100', pump, {'pump_supported': False, 'pump_off_level': -1}))
check(not console.validate_command('pump on 100', pump, {'pump_supported': True, 'pump_off_level': 1}))
check(console.validate_command('pump on 100', pump, {'pump_supported': True, 'pump_off_level': 0}))
check(not console.validate_command('pump on 101', pump, {'pump_supported': True, 'pump_off_level': 0}))
check(not console.validate_command('pump on 4294967396', pump, {'pump_supported': True, 'pump_off_level': 0}))

build_path = ROOT / 'build_safe_txatomic/result.json'
build = json.loads(build_path.read_text())
image = Path(build['image'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
check(sha(image) == build['image_sha256'] and image.stat().st_size == build['image_bytes'])
for name, meta in build['source_manifest'].items():
    check(sha(ROOT / 'firmware' / name) == meta['sha256'])
regression = json.loads((ROOT / 'verification_tx_atomic/result.json').read_text())
check(regression['status'] == 'SIMULATION_PASS' and regression['integration_cases'] == 30)
check(regression['maximum_frame_bytes'] <= 8192)
receipt = {'created_utc': datetime.now(timezone.utc).isoformat(), 'release_identity': 'VERIFIED_PASS',
           'new_helper_checks': checks, 'helper_runtime_tests': 'SIMULATION_ONLY', 'commands': commands,
           'build_result': str(build_path), 'build_result_sha256': sha(build_path),
           'image': str(image), 'image_bytes': image.stat().st_size, 'image_sha256': sha(image),
           'regression_result_sha256': sha(ROOT / 'verification_tx_atomic/result.json'),
           'APP_FLASH': 'NO_GO', 'pump_off_level': -1, 'physical_pass': False,
           'manual_console_Jetson_device_runtime': 'NOT_RUN',
           'files': {p.name: sha(p) for p in (ROOT / 'manual_console.py', ROOT / 'flash_plan.py', ROOT / 'build.py')}}
(ROOT / 'RELEASE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k not in ('files', 'commands')}, indent=2))
