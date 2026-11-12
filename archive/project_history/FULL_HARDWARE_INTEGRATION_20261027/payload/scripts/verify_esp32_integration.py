"""Run native bridge/policy and Python PTY/API tests; never use physical devices."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/overnight_integration_20261023' / ('checks_' + datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S'))
OUT.mkdir()
records = []


def run(name, command, timeout=180):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout, env={**os.environ, 'PYTHONPATH': str(ROOT / 'jetson') + ':' + str(ROOT)})
    (OUT / (name + '.log')).write_bytes(result.stdout)
    records.append({'name': name, 'command': [str(x) for x in command], 'exit_code': result.returncode})
    (OUT / 'commands.json').write_text(json.dumps(records, indent=2))
    print(result.stdout.decode('utf-8', 'replace'), flush=True)
    if result.returncode:
        raise SystemExit(name + ' FAILED; see ' + str(OUT))


run('native_bridge_build', ['sh', ROOT / 'scripts/build_esp32_bridge.sh'])
run('native_policy_ubsan_build', ['g++', '-std=c++14', '-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=undefined',
                                '-Wall', '-Wextra', '-Wpedantic', '-Werror', ROOT / 'jetson/device/test_policy.cpp',
                                '-ljson-c', '-o', ROOT / '.native-build/esp32/test_policy'])
run('native_policy_ubsan', [ROOT / '.native-build/esp32/test_policy', ROOT / 'jetson/tests/fixtures/esp32_current.synthetic.json'])
run('decision_ubsan_build', ['g++', '-std=c++14', '-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=undefined',
                             '-Wall', '-Wextra', '-Wpedantic', '-Werror', ROOT / 'jetson/device/test_decision.cpp',
                             '-o', ROOT / '.native-build/esp32/test_decision'])
run('decision_ubsan', [ROOT / '.native-build/esp32/test_decision'])
run('new_pty_api_tests', [sys.executable, '-m', 'pytest', 'jetson/tests/test_esp32_bridge.py', 'jetson/tests/test_device_state_api.py',
                          'jetson/tests/test_system_state.py', 'jetson/tests/test_ai_state_tap.py', 'jetson/tests/test_dry_run_requests.py',
                          'jetson/tests/test_schedule_gate.py', '-q', '-ra'])
print('CHECKS_PASS', OUT)
