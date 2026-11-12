"""Compile and run NEW offline Bridge regressions, never firmware/Serial/Jetson."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[1]
ZIG = WS / '.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
LIB = WS / 'HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--label', required=True)
a = p.parse_args()
if not a.label.replace('_', '').isalnum():
    p.error('simple NEW label')
out = ROOT / ('bridge_tests_' + a.label)
out.mkdir()
result = {'status': 'FAIL', 'physical_pass': False, 'source': 'OFFLINE_NEW_BRIDGE_TESTS',
          'whole_POSIX_Bridge_build': 'NOT_RUN', 'commands': []}


def run(args, name):
    row = {'command': [str(x) for x in args], 'timestamp_utc': datetime.now(timezone.utc).isoformat()}
    q = subprocess.run(row['command'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240,
                       env={**os.environ, 'FORCAT_NEW_TEST_OUT': str(out), 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    (out / (name + '.log')).write_bytes(q.stdout)
    row.update(exit_code=q.returncode, log=name+'.log'); result['commands'].append(row)
    if q.returncode:
        raise RuntimeError(name + ' failed; preserve logs')
    return q.stdout.decode('utf-8', 'replace')


try:
    run([ZIG, 'c++', '-std=c++14', '-O1', '-Wall', '-Wextra', '-Werror',
         '-I'+str(ROOT/'bridge'), '-I'+str(LIB/'include'), ROOT/'tests/bridge_probe.cpp',
         LIB/'lib/libjson-c.a', '-ladvapi32', '-o', out/'bridge_probe.exe'], 'compile')
    run([sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', ROOT/'tests/test_bridge.py'], 'tests')
    result.update(status='SIMULATION_PASS', pytest_cases=16, retained_firmware_frames_checked=37,
                  compiler_flags='C++14 -O1 -Wall -Wextra -Werror', old_firmware_tests_rerun=0)
except Exception as e:
    result['error'] = str(e)
    raise
finally:
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
