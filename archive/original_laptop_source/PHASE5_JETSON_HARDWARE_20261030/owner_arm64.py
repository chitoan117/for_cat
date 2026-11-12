"""Python3.6+ handoff wrapper: default PLAN, explicit new-staging file-only build.

No SSH, serial/camera APIs, service mutations, installs, POST or production DB.
Run only after reviewing the read-only preflight. Failures preserve NEW evidence.
"""
from __future__ import print_function
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ZIP_SHA = '1c3b8abaf2586d91ac468c8c632d8750bf28a72d92f91130b983cb51dd99990d'
MANIFEST_SHA = 'a92fc2586daacaabb5e931f0b8603bb1a3bd159a1cd747f43fd8b0cff0a968d4'
VERIFIER_SHA = '5338e1200423241177cb52680ca225ef499eaa8fdc622c59250394a433a0d5f6'
ROOT = Path(__file__).resolve().parent
UNITS = ('for-cat-ai.service', 'for-cat-api.service', 'for-cat-esp32-bridge.service')
BYID = '/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', choices=('BUILD_AND_FILE_REPLAY_ONLY',))
    a = p.parse_args()
    if not a.execute:
        print(json.dumps({'mode': 'PLAN_ONLY', 'expected_staging': '/home/toan/phase5_for_cat_20261030_*',
            'source_manifest_sha256': MANIFEST_SHA, 'single_cpu': True, 'nice_increment': 15,
            'minimum_MemAvailable_MiB': 768, 'compiler_address_space_cap_MiB': 512,
            'minimum_free_disk_MiB': 256, 'APP_FLASH': 'NO_GO', 'SERVO_PUMP': 'LOCKED'}))
        return 0
    if platform.system() != 'Linux' or platform.machine().lower() not in ('aarch64', 'arm64'):
        raise ValueError('actual Linux ARM64 required')
    if ROOT.parent != Path('/home/toan') or not ROOT.name.startswith('phase5_for_cat_20261030_'):
        raise ValueError('NEW dedicated staging directly under /home/toan required')
    if ROOT.is_symlink() or (ROOT / 'source').exists() or (ROOT / 'source').is_symlink():
        raise ValueError('no existing source root may be reused/overwritten')
    out = ROOT / ('owner_run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(mode=0o700)
    result = {'source': 'ACTUAL_JETSON_EXECUTION', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'ARM64_PASS': False, 'physical_pass': False, 'APP_FLASH': 'NO_GO',
              'SERVO_PUMP': 'LOCKED', 'commands': [], 'output': str(out)}
    code = 2

    def run(argv, label, expected=0, timeout=60, limited=False):
        def limits():
            import resource
            os.nice(15)
            os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        result['stage'] = label
        row = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'command': [str(x) for x in argv]}
        try:
            q = subprocess.run(row['command'], cwd=str(ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=timeout, preexec_fn=limits if limited else None)
            output, rc = q.stdout, q.returncode
        except subprocess.TimeoutExpired as e:
            output, rc = (e.stdout or b'') + b'\nTIMEOUT\n', 124
        (out / (label + '.log')).write_bytes(output)
        row.update(exit_code=rc, log=str(out / (label + '.log')), sha256=hashlib.sha256(output).hexdigest())
        result['commands'].append(row)
        if rc != expected:
            raise RuntimeError(label + ' exit=' + str(rc))
        return output.decode('utf-8', 'replace')

    def services(label):
        snap = {}
        for index, unit in enumerate(UNITS):
            text = run(['systemctl', '--user', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState'], label + '_unit' + str(index))
            row = dict(x.split('=', 1) for x in text.splitlines() if '=' in x)
            if row.get('ActiveState') != 'active' or row.get('SubState') != 'running' or int(row.get('MainPID', '0')) <= 0:
                raise ValueError('existing production service not active/running: ' + unit)
            row['exe'] = os.readlink('/proc/' + row['MainPID'] + '/exe')
            row['binary_sha256'] = sha(Path('/proc') / row['MainPID'] / 'exe')
            snap[unit] = row
        if Path(BYID).resolve(strict=True) != Path('/dev/ttyACM0'):
            raise ValueError('unexpected USB identity path')
        holders = run(['fuser', '/dev/ttyACM0'], label + '_serial_owner')
        # fuser stderr may include /dev/ttyACM0:; compare standalone numeric PIDs only.
        pids = re.findall(r'(?<![\w/])\b[0-9]+\b(?![\w/])', holders.replace('/dev/ttyACM0:', ''))
        if pids != [snap[UNITS[-1]]['MainPID']]:
            raise ValueError('serial owner is not sole current Bridge PID')
        if snap[UNITS[-1]]['exe'] != '/home/toan/for_cat/.native-build/esp32/esp32_bridge':
            raise ValueError('unexpected production Bridge executable')
        return snap

    try:
        result['host'] = {'hostname': platform.node(), 'machine': platform.machine(), 'python': platform.python_version()}
        archive, verifier = ROOT / 'R2_HARDENING_SOURCE.zip', ROOT / 'safe_release.py'
        if archive.is_symlink() or verifier.is_symlink() or archive.stat().st_size != 288687 or sha(archive) != ZIP_SHA or sha(verifier) != VERIFIER_SHA:
            raise ValueError('transfer integrity mismatch')
        result['transfer'] = {'zip_sha256': ZIP_SHA, 'source_manifest_sha256': MANIFEST_SHA, 'verifier_sha256': VERIFIER_SHA}
        run(['sh', ROOT / 'jetson_preflight.sh'], 'read_only_preflight', timeout=150)
        result['production_before'] = services('before')
        mem = dict(x.split(':', 1) for x in Path('/proc/meminfo').read_text().splitlines())
        available = int(mem['MemAvailable'].split()[0]) // 1024
        free = shutil.disk_usage(str(ROOT)).free // (1024 * 1024)
        result['resources'] = {'MemAvailable_MiB': available, 'free_disk_MiB': free,
                               'load_average': list(os.getloadavg()), 'single_cpu': True, 'nice_increment': 15,
                               'child_RLIMIT_AS_MiB': 512}
        if available < 768 or free < 256:
            raise ValueError('BLOCKED_RESOURCES: need >=768MiB MemAvailable and >=256MiB free disk; do not stop services')
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                name = (proc / 'comm').read_text().strip()
            except OSError:
                continue
            if name in ('g++', 'gcc', 'cc1', 'cc1plus', 'clang', 'clang++'):
                raise ValueError('another compiler already active; do not start concurrent build')
        version = run(['g++', '--version'], 'compiler')
        if not re.search(r'\b7\.5\.0\b', version):
            raise ValueError('actual GCC7.5.0 required')
        run(['pkg-config', '--modversion', 'json-c', 'sqlite3'], 'dependency_versions')
        run(['python3', '-B', verifier, '--archive', archive, '--expected-sha256', MANIFEST_SHA], 'archive_verify')
        source = ROOT / 'source'
        run(['python3', '-B', verifier, '--archive', archive, '--extract-to', source, '--expected-sha256', MANIFEST_SHA], 'safe_extract')
        run(['python3', '-B', source / 'tools/safe_release.py', '--directory', source, '--expected-sha256', MANIFEST_SHA], 'source_verify')
        native = source / 'tools/native_hardening.py'
        run(['python3', '-B', native], 'native_plan')
        native_out = source / ('hardening_arm64_' + out.name)
        result['native_output'] = str(native_out)
        run(['python3', '-B', native, '--execute', 'BUILD_AND_FILE_REPLAY_ONLY', '--expected-sha256', MANIFEST_SHA,
             '--out', native_out], 'native_execute', timeout=1800, limited=True)
        actual = json.loads((native_out / 'result.json').read_text())
        if actual.get('ARM64_NATIVE_TEST_PASS') is not True or actual.get('native_summaries') != {
            'safety_audit': [12, 101], 'mass_policy': [11, 58], 'session_audit': [9], 'behavior_hardening': [134]
        } or actual.get('stream_records') != 24:
            raise ValueError('missing/mismatched actual native success evidence')
        result['native_result_sha256'] = sha(native_out / 'result.json')
        result['binary_sha256'] = actual['binary_sha256']
        result['ARM64_PASS'] = True
        result['whole_posix_bridge_compile'] = 'PASS'
        result['production_after'] = services('after')
        result['production_identity_unchanged'] = result['production_before'] == result['production_after']
        if not result['production_identity_unchanged']:
            raise ValueError('production PID/state/binary changed during run; review without restarting')
        code = 0
        result['stage'] = 'COMPLETE'
    except Exception as e:
        result['error'] = type(e).__name__ + ': ' + str(e)
    finally:
        result.update(exit_code=code, finished_utc=datetime.now(timezone.utc).isoformat())
        with (out / 'result.json').open('x') as f:
            json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
