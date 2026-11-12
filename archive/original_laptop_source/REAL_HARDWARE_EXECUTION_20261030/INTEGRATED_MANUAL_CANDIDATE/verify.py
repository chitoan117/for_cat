"""New integration regressions only; actual firmware setup/loop with host GPIO fakes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
FW = ROOT / 'firmware'
WS = ROOT.parents[1]
ZIG = WS / '.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
CASES = ('boot_and_bounds', 'mutual_exclusion', 'pump_timeout_and_limits', 'replay_and_emergency',
         'reconnect_budgets', 'backpressure_deadline', 'clock_and_input_faults', 'overlong_input',
         'sensor_calibration_telemetry', 'buzzer_manual_only')
p = argparse.ArgumentParser()
p.add_argument('--label', required=True)
a = p.parse_args()
if not a.label.replace('_', '').isalnum():
    p.error('simple NEW label')
out = ROOT / ('verification_' + a.label)
out.mkdir()
records = []
result = {'status': 'FAIL', 'source': 'SIMULATED_NEW_INTEGRATION_ONLY', 'physical_pass': False,
          'commands': records, 'cases': []}


def run(argv, label):
    row = {'command': [str(x) for x in argv], 'timestamp_utc': datetime.now(timezone.utc).isoformat()}
    q = subprocess.run(row['command'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=240, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    (out / (label + '.log')).write_bytes(q.stdout)
    row.update(exit_code=q.returncode, log=label + '.log')
    records.append(row)
    if q.returncode:
        raise RuntimeError(label + ' failed, output retained')
    return q.stdout.decode('utf-8', 'replace')


try:
    for level in (-1, 0, 1):
        variant = 'inert' if level == -1 else 'off' + str(level)
        exe = out / (variant + '.exe')
        run([ZIG, 'c++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror',
             '-DMANUAL_PUMP_OFF_LEVEL=' + str(level), '-I' + str(FW / 'test/arduino_stub'),
             '-I' + str(FW / 'include'), ROOT / 'tests/integrated_loop.cpp', '-o', exe], variant + '_compile')
        for case in CASES:
            label = variant + '_' + case
            text = run([exe, case, out / (label + '.serial.log')], label)
            assert 'INTEGRATED_PASS' in text
            result['cases'].append({'variant': variant, 'case': case, 'summary': text.strip()})
    frames = []
    for path in out.glob('*.serial.log'):
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('{'):
                frame = json.loads(line)
                assert frame['mode'] == 'diag_manual_station' and frame['kit_profile'] == 'diag_manual_station'
                assert frame['manual_station']['physical_pass'] is False
                assert frame['manual_station']['automatic_execution'] is False
                assert len(line.encode()) <= 8192
                frames.append(len(line.encode()))
    assert frames
    result.update(status='SIMULATION_PASS', integration_cases=len(result['cases']),
                  telemetry_frames_checked=len(frames), maximum_frame_bytes=max(frames),
                  pump_polarity_physically_verified=False,
                  reused_controller_SHA256={name: hashlib.sha256((FW / 'include/m4' / name).read_bytes()).hexdigest()
                                           for name in ('servo_bench.h', 'pump_bench.h')})
except Exception as e:
    result['error'] = type(e).__name__ + ': ' + str(e)
    raise
finally:
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('commands', 'cases')}, indent=2))
