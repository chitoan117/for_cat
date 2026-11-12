"""OWNER-run GCC7.5 ARM64 R2 build/file replay. Default PLAN, no deployment.
Only executes fixed compilers, file-test programs and the Bridge's default PLAN.
"""
from __future__ import print_function
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import native_checks as checks
from verify_transfer import verify
ROOT=Path(__file__).resolve().parent

def output_path(value,root=ROOT):
    root=Path(root).resolve();p=Path(value)
    if p.is_symlink() or p.exists():raise ValueError('output exists; preserve every R1/R2 run')
    p=p.resolve()
    if p.parent!=root or not p.name.startswith('native_arm64_r2_'):raise ValueError('NEW direct native_arm64_r2_* directory under R2 root required')
    return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',choices=('BUILD_AND_FILE_REPLAY_ONLY',));p.add_argument('--out',type=Path,default=ROOT/'native_arm64_r2_first_run')
    p.add_argument('--expected-sha256');a=p.parse_args()
    plan={'mode':'PLAN_ONLY','revision':'GCC75_R2','host':platform.system(),'machine':platform.machine(),
        'output':str(a.out),'ARM64_NATIVE_TEST_PASS':'NOT_RUN','serial_opened':False,'camera_opened':False,
        'services_changed':False,'physical_pass':False,'APP_FLASH':'NO_GO',
        'builds':['parser_replay','test_session','test_food_roi','logic_tests','timeline_probe','dispense_regressions','esp32_bridge'],
        'requirements':['Linux aarch64/arm64','g++7.5.0 C++14','pkg-config json-c sqlite3 development libraries'],
        'resource_policy':'one compiler at a time, O1, no package installation or runtime service cutover',
        'Bridge_execution':'default PLAN and negative dog-warning rejection only; never --live-serial'}
    if not a.execute:
        print(json.dumps(plan,indent=2));return
    if platform.system()!='Linux' or platform.machine().lower() not in ('aarch64','arm64'):raise ValueError('R2 acceptance requires actual Linux ARM64; no Windows/cross-compile promotion')
    target=output_path(a.out)
    integrity=verify(expected=a.expected_sha256)
    if not shutil.which('g++') or not shutil.which('pkg-config'):raise ValueError('missing existing compiler/dependencies; no automatic install')
    target.mkdir(mode=0o700);(target/'fixtures').mkdir()
    result=dict(plan,mode='BUILD_AND_FILE_REPLAY_ONLY',ARM64_NATIVE_TEST_PASS=False,
        started_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),transfer=integrity,
        whole_posix_bridge_compile='NOT_RUN')
    def run(argv,name,expected_code=0):
        result['stage']=name
        try:q=subprocess.run([str(x) for x in argv],cwd=target,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        except subprocess.TimeoutExpired as error:
            (target/(name+'.log')).write_bytes((error.stdout or b'')+b'\nTIMEOUT_300S\n')
            raise
        (target/(name+'.log')).write_bytes(q.stdout)
        if q.returncode!=expected_code:raise RuntimeError(name+' failed; exit='+str(q.returncode))
        return q.stdout.decode('utf-8','replace')
    try:
        compiler=run(['g++','--version'],'compiler').splitlines()[0]
        if not re.search(r'\b7\.5\.0\b',compiler):raise ValueError('this acceptance targets GCC7.5.0; retain version output and request review')
        result['compiler']=compiler
        result['dependency_versions']=run(['pkg-config','--modversion','json-c','sqlite3'],'dependency_versions').splitlines()
        flags=shlex.split(run(['pkg-config','--cflags','--libs','json-c','sqlite3'],'dependencies').strip())
        common=['g++','-std=c++14','-O1','-Wall','-Wextra','-Werror',
            '-I'+str(ROOT/'candidate/bridge'),'-I'+str(ROOT/'candidate/firmware/include'),'-I'+str(ROOT/'candidate/protocol')]
        result['compile_flags']=common[1:]
        targets=(('parser_replay','candidate/bridge/parser_replay.cpp'),('test_session','candidate/bridge/test_session.cpp'),
            ('test_food_roi','candidate/bridge/test_food_roi.cpp'),('logic_tests','tests/logic_tests.cpp'),
            ('timeline_probe','tests/timeline_probe.cpp'),('dispense_regressions','tests/dispense_regressions.cpp'),
            ('esp32_bridge','candidate/bridge/esp32_bridge.cpp'))
        for name,source in targets:run(common+[ROOT/source]+flags+['-o',target/name],name+'_compile')
        result['whole_posix_bridge_compile']='PASS'
        result['native_tests']=checks.collect_program_results(target,'',run)
        before=set(x.name for x in target.iterdir())
        response=json.loads(run([target/'esp32_bridge','--db',target/'MUST_NOT_CREATE.sqlite3','--log',target/'MUST_NOT_CREATE.jsonl'],'bridge_default_plan'))
        if response.get('mode')!='PLAN_ONLY' or response.get('serial_opened') is not False or response.get('actuator_tx') is not False:raise ValueError('default Bridge did not remain PLAN')
        added=set(x.name for x in target.iterdir())-before
        if added!={'bridge_default_plan.log'}:raise ValueError('unexpected default Bridge filesystem side effect')
        run([target/'esp32_bridge','--dog-warning','1'],'bridge_reject_dog_warning',expected_code=1)
        if any((target/x).exists() for x in ('MUST_NOT_CREATE.sqlite3','MUST_NOT_CREATE.jsonl','MUST_NOT_CREATE.sqlite3-esp32.lock')):raise ValueError('Bridge created forbidden sentinel files')
        result['transfer_after_tests']=verify(expected=integrity['manifest_sha256'])
        result.update(ARM64_NATIVE_TEST_PASS=True,stage='COMPLETE',
            binary_sha256={n:hashlib.sha256((target/n).read_bytes()).hexdigest() for n,_ in targets})
    except BaseException as error:
        result['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        checks.write_json(target/'result.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
