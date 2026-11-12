"""Python 3.6+ owner-run Linux ARM64 build/file replay. Default PLAN only.
Never starts the live bridge, accesses serial/camera, or invokes service tools.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import platform
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
SOURCES = HERE / 'bridge_candidate'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(argv, out, name):
    p = subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=240)
    (out / (name + '.log')).write_bytes(p.stdout)
    if p.returncode:
        raise RuntimeError(name + ' failed; see ' + str(out / (name + '.log')))
    return p.stdout.decode('utf-8', 'replace')

def replay(exe, out):
    fixture = KIT / 'test_output/quad_firmware_loop_test.log'
    values = [json.loads(x) for x in fixture.read_text().splitlines() if x.startswith('{')]
    if len(values) != 2:
        raise ValueError('expected two full OFFLINE_TEST_ONLY firmware fixtures')
    tested = []
    def check(name, lines, chunk, accepted, rejected=0, oversized=0):
        path = out / (name + '.input')
        path.write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
        text = run([exe, path, chunk], out, name)
        rows = [json.loads(x) for x in text.splitlines()]
        summary = rows[-1]
        if (summary['accepted'], summary['rejected'], summary['oversized']) != (accepted, rejected, oversized):
            raise ValueError(name + ': replay counts mismatch')
        tested.append(name)
        return rows
    lines = [json.dumps(x, separators=(',', ':')) for x in values]
    if not all(len(x) > 4096 for x in lines):
        raise ValueError('full firmware report fixture unexpectedly truncated')
    for chunk in (1, 7, 127, 1024, 2048, 8192):
        rows = check('fragment_' + str(chunk), lines, chunk, 2)
        t = rows[0]['telemetry']
        if t['mode'] != 'diag_current_hardware' or t['diagnostic_profile'] != 'diag_four_ultrasonic':
            raise ValueError('wire mode/profile was rewritten')
        if len(t['ultrasonic']) != 4 or t['sensors']['buzzer']['capability'] is not False:
            raise ValueError('unexpected sensors/manual buzzer capability')
    boundary = lines[0] + ' ' * (8192-len(lines[0]))
    check('boundary_8192', [boundary], 1024, 1)
    check('oversized_8193', [boundary+' '], 1024, 0, oversized=1)
    mutations = []
    for mode in ('HX711_REFERENCE', 'diag_four_ultrasonic', 'diag_servo_bench', 'diag_pump_bench'):
        x = json.loads(lines[0]); x['mode'] = mode; mutations.append(x)
    for key in ('kit_profile', 'kit_firmware_id', 'weight', 'ultrasonic', 'motion_valid'):
        x = json.loads(lines[0]); del x[key]; mutations.append(x)
    for key in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water'):
        x = json.loads(lines[0]); x['current_hardware'][key] = True; mutations.append(x)
    for sensor in ('HC_SR04_1', 'HC_SR04_2', 'JSN_SR04T_1', 'JSN_SR04T_2'):
        x = json.loads(lines[0]); x['ultrasonic'][sensor]['echo_gpio'] = 6; mutations.append(x)
    for index, x in enumerate(mutations):
        check('rejected_' + str(index), [json.dumps(x, separators=(',', ':'))], 7, 0, rejected=1)
    x = json.loads(lines[0]); x['current_hardware']['servo_armed'] = True
    rows = check('unsafe_latch', [json.dumps(x, separators=(',', ':')), lines[0]], 7, 1, rejected=1)
    if rows[-1]['health_before_file_close'] != 'ESP32_BAD_TELEMETRY':
        raise ValueError('unsafe latch cleared by good frame')
    return tested

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', choices=('BUILD_AND_FILE_REPLAY_ONLY',))
    p.add_argument('--out', type=Path, default=HERE/'native_arm64_gcc75_r1')
    a = p.parse_args()
    plan = {'mode':'PLAN_ONLY', 'host':platform.system(), 'machine':platform.machine(),
            'source':str(SOURCES), 'output':str(a.out), 'serial_opened':False,
            'camera_opened':False, 'services_changed':False, 'physical_pass':False,
            'requires':['Linux aarch64/arm64', 'g++ C++14', 'pkg-config', 'json-c headers/library', 'SQLite3 headers/library'],
            'kit_revision':'GCC75_R1',
            'builds':['parser_replay', 'test_session', 'test_food_roi', 'esp32_bridge'],
            'execution':'only FOOD_ROI/parser/session file tests and esp32_bridge default PLAN; no --live-serial',
            'resource_policy':'one compiler at a time; O1; owner chooses idle window; logs bounded by test corpus',
            'ARM64_NATIVE_TEST_PASS':'NOT_RUN'}
    if not a.execute:
        print(json.dumps(plan, indent=2)); return
    if platform.system() != 'Linux' or platform.machine().lower() not in ('aarch64','arm64'):
        raise ValueError('native acceptance requires Linux ARM64; cross compilation is not acceptance')
    out = a.out.resolve()
    out.relative_to(HERE)
    if out.parent != HERE or not out.name.startswith('native_arm64_') or out.exists():
        raise ValueError('output must be a NEW direct native_arm64_* directory under web_hardware')
    if not out.parent.is_dir():
        raise ValueError('output parent does not exist')
    if not shutil.which('g++') or not shutil.which('pkg-config'):
        raise ValueError('missing compiler/pkg-config; no automatic package installation')
    out.mkdir()
    result = dict(plan, mode='BUILD_AND_FILE_REPLAY_ONLY', ARM64_NATIVE_TEST_PASS=False)
    try:
        flags = shlex.split(run(['pkg-config','--cflags','--libs','json-c','sqlite3'],out,'dependencies').strip())
        result['dependency_versions'] = run(['pkg-config','--modversion','json-c','sqlite3'],out,'dependency_versions').splitlines()
        result['compiler'] = run(['g++','--version'],out,'compiler').splitlines()[0]
        result['source_sha256'] = {x.relative_to(KIT).as_posix():digest(x) for x in sorted(SOURCES.iterdir()) if x.suffix in ('.h','.cpp')}
        result['protocol_header_sha256'] = digest(KIT/'firmware/include/dog_warning_protocol.h')
        result['fixture_sha256'] = digest(KIT/'test_output/quad_firmware_loop_test.log')
        common = ['g++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(SOURCES),'-I'+str(KIT/'firmware/include')]
        for name in ('parser_replay','test_session','test_food_roi','esp32_bridge'):
            run(common+[SOURCES/(name+'.cpp')]+flags+['-o',out/name],out,name+'_compile')
        roi = run([out/'test_food_roi'],out,'food_roi_tests').strip()
        if 'FOOD_ROI_PASS groups=10 checks=115 ' not in roi:
            raise ValueError('FOOD_ROI edge/negative groups did not pass')
        result['food_roi_stdout'] = roi
        result['food_roi_groups'] = 10
        result['food_roi_checks'] = 115
        session = run([out/'test_session'],out,'session_tests').strip()
        if 'PASS' not in session or '17' not in session:
            raise ValueError('session tests did not report 17 PASS checks')
        result['session_stdout'] = session
        result['replay_cases'] = replay(out/'parser_replay',out)
        sentinel = out/'MUST_NOT_CREATE.sqlite3'
        before = set(x.name for x in out.iterdir())
        text = run([out/'esp32_bridge','--db',sentinel,'--log',out/'MUST_NOT_CREATE.jsonl'],out,'bridge_default_plan')
        response = json.loads(text)
        if response.get('mode') != 'PLAN_ONLY' or response.get('serial_opened') is not False or sentinel.exists():
            raise ValueError('bridge default did not remain side-effect-free PLAN')
        added = set(x.name for x in out.iterdir()) - before
        if added != {'bridge_default_plan.log'}:
            raise ValueError('unexpected bridge default filesystem effects')
        result.update(ARM64_NATIVE_TEST_PASS=True, whole_posix_bridge_compile='PASS',
                      binary_sha256={n:digest(out/n) for n in ('parser_replay','test_session','test_food_roi','esp32_bridge')})
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
