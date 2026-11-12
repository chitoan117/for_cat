"""Python3.6+ OWNER native build/file tests. PLAN default, never deploy/live serial."""
from __future__ import print_function
import argparse,hashlib,json,platform,re,shlex,shutil,subprocess
from pathlib import Path
from safe_release import directory
ROOT=Path(__file__).resolve().parents[1]
def new_output(value):
    p=Path(value)
    if p.exists() or p.is_symlink():raise ValueError('preserve all existing R1/R2/hardening outputs')
    p=p.resolve()
    if p.parent!=ROOT or not p.name.startswith('hardening_arm64_'):raise ValueError('NEW direct hardening_arm64_* child required')
    return p
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',choices=('BUILD_AND_FILE_REPLAY_ONLY',))
    p.add_argument('--out',type=Path,default=ROOT/'hardening_arm64_first_run');p.add_argument('--expected-sha256');a=p.parse_args()
    result={'mode':'PLAN_ONLY','revision':'R2_OFFLINE_HARDENING_PM5','base':'GCC75_R2','ARM64_NATIVE_TEST_PASS':'NOT_RUN',
        'APP_FLASH':'NO_GO','serial_opened':False,'camera_opened':False,'services_changed':False,'physical_pass':False,
        'mass_policy':{'target_grams':35,'tolerance_grams':5,'accepted_minimum':30,'accepted_maximum':40,'control_aim':35},
        'output':str(a.out),'operations':'sequential GCC7.5 C++14 builds, fake-output/file tests and Bridge default PLAN only'}
    if not a.execute:print(json.dumps(result,indent=2));return
    if platform.system()!='Linux' or platform.machine().lower() not in ('aarch64','arm64'):raise ValueError('actual Linux ARM64 required, no Windows/cross-build promotion')
    if not a.expected_sha256:raise ValueError('trusted external source-manifest digest required')
    out=new_output(a.out);result['source_before']=directory(ROOT,a.expected_sha256,allow_generated=True)
    if not shutil.which('g++') or not shutil.which('pkg-config'):raise ValueError('existing compiler/development libs required; no automatic install')
    out.mkdir(mode=0o700);result.update(mode='BUILD_AND_FILE_REPLAY_ONLY',ARM64_NATIVE_TEST_PASS=False)
    def run(argv,label,code=0):
        result['stage']=label
        try:q=subprocess.run([str(x) for x in argv],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        except subprocess.TimeoutExpired as e:(out/(label+'.log')).write_bytes((e.stdout or b'')+b'\nTIMEOUT\n');raise
        (out/(label+'.log')).write_bytes(q.stdout)
        if q.returncode!=code:raise RuntimeError(label+' exit='+str(q.returncode))
        return q.stdout.decode('utf-8','replace')
    try:
        version=run(['g++','--version'],'compiler').splitlines()[0];result['compiler']=version
        if not re.search(r'\b7\.5\.0\b',version):raise ValueError('GCC7.5.0 qualification requested; retain actual version')
        flags=shlex.split(run(['pkg-config','--cflags','--libs','json-c','sqlite3'],'dependencies').strip())
        result['dependency_versions']=run(['pkg-config','--modversion','json-c','sqlite3'],'versions').splitlines()
        common=['g++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(ROOT/'candidate/bridge'),
            '-I'+str(ROOT/'candidate/firmware/include'),'-I'+str(ROOT/'candidate/protocol')]
        targets=('safety_audit','mass_policy','session_audit','stream_bridge','behavior_hardening')
        for name in targets:run(common+[ROOT/'tests'/(name+'.cpp')]+flags+['-o',out/name],name+'_compile')
        run(common+[ROOT/'candidate/bridge/esp32_bridge.cpp']+flags+['-o',out/'esp32_bridge'],'bridge_compile')
        summaries={}
        for name,pattern in (
            ('safety_audit',r'HARDENING_SAFETY_PASS cases=(\d+) checks=(\d+)'),
            ('mass_policy',r'MASS_POLICY_PASS cases=(\d+) checks=(\d+) target=35 tolerance=5'),
            ('session_audit',r'HARDENING_SESSION_PASS checks=(\d+)'),
            ('behavior_hardening',r'BEHAVIOR_HARDENING_PASS checks=(\d+)')):
            text=run([out/name],name+'_tests');m=re.search(pattern,text)
            if not m:raise ValueError('test summary missing: '+name)
            summaries[name]=list(map(int,m.groups()))
        rows=[json.loads(x) for x in run([out/'stream_bridge',ROOT/'fixtures/transport_script.json'],'stream_tests').splitlines()]
        if len(rows)!=24 or any(x.get('source')!='SIMULATED' for x in rows):raise ValueError('scripted replay missing/provenance mismatch')
        by_case={x['case']:x for x in rows}
        for name,health in (('healthy_cat','ESP32_CONNECTED'),('duplicate_frozen','ESP32_STALE'),('out_of_order','ESP32_BAD_TELEMETRY'),
            ('reconnect_fresh','ESP32_CONNECTED'),('unsafe_still_latched','ESP32_BAD_TELEMETRY')):
            if by_case[name]['health']!=health:raise ValueError('replay state mismatch: '+name)
        good=by_case['healthy_cat']['telemetry']
        if good['mode']!='diag_current_hardware' or good['diagnostic_profile']!='diag_four_ultrasonic' or len(good['ultrasonic'])!=4:raise ValueError('wire/profile sensor contract changed')
        before=set(x.name for x in out.iterdir())
        response=json.loads(run([out/'esp32_bridge','--db',out/'MUST_NOT_CREATE.db','--log',out/'MUST_NOT_CREATE.log'],'bridge_default_plan'))
        if response.get('mode')!='PLAN_ONLY' or response.get('serial_opened') is not False or response.get('actuator_tx') is not False:raise ValueError('Bridge did not stay PLAN')
        if set(x.name for x in out.iterdir())-before!={'bridge_default_plan.log'}:raise ValueError('unexpected default Bridge side effect')
        run([out/'esp32_bridge','--dog-warning','1'],'dog_warning_rejected',1)
        result['source_after']=directory(ROOT,a.expected_sha256,allow_generated=True)
        result.update(ARM64_NATIVE_TEST_PASS=True,stage='COMPLETE',native_summaries=summaries,stream_records=len(rows),
            binary_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in targets+('esp32_bridge',)})
    except BaseException as error:result['error']=type(error).__name__+': '+str(error);raise
    finally:
        with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
