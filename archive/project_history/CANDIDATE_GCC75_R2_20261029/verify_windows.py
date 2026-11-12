"""Fresh R2 Windows regression run; all products go to a NEW local directory."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import native_checks as checks
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args()
    out=(a.out or HERE/('validation_windows_'+datetime.now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if out.parent!=HERE or not out.name.startswith('validation_windows_') or out.exists() or out.is_symlink():raise ValueError('NEW direct validation_windows_* directory required')
    out.mkdir();(out/'fixtures').mkdir()
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8','FLUTTER_SUPPRESS_ANALYTICS':'true','FORCAT_R2_OUTPUT':str(out)}
    result={'revision':'GCC75_R2','host':'WINDOWS','ARM64_NATIVE_TEST_PASS':'NOT_RUN','physical_pass':False,
        'serial_opened':False,'camera_opened':False,'services_changed':False,'APP_FLASH':'NO_GO'}
    def run(args,name):
        q=subprocess.run([str(x) for x in args],cwd=HERE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240,env=env)
        (out/(name+'.log')).write_bytes(q.stdout)
        print(name+': '+('PASS' if q.returncode==0 else 'FAIL'),flush=True)
        if q.returncode:raise RuntimeError(name+' failed: '+str(out/(name+'.log')))
        return q.stdout.decode('utf-8','replace')
    try:
        common=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE/'candidate/bridge'),'-I'+str(HERE/'candidate/firmware/include')]
        json_inc='-I'+str(KIT/'web_hardware/native_jsonc_install/include')
        lib=KIT/'web_hardware/native_jsonc_install/lib/libjson-c.a'
        for name,path,with_json in (
            ('parser_replay','candidate/bridge/parser_replay.cpp',True),('test_session','candidate/bridge/test_session.cpp',False),
            ('test_food_roi','candidate/bridge/test_food_roi.cpp',False),('logic_tests','tests/logic_tests.cpp',False),
            ('timeline_probe','tests/timeline_probe.cpp',True),('dispense_regressions','tests/dispense_regressions.cpp',False)):
            run(common+([json_inc] if with_json else [])+[HERE/path]+([lib,'-ladvapi32'] if with_json else [])+['-o',out/(name+'.exe')],name+'_compile')
        # Reproduce uncovered overnight branches, not the fixed R1 formatting issue.
        old=ROOT/'OVERNIGHT_ENGINEERING_20261029/offline_continuation/candidate/firmware/include'
        base_common=[x for x in common if not str(x).startswith('-I'+str(HERE/'candidate/firmware/include'))]
        run(base_common+['-I'+str(old),HERE/'tests/dispense_regressions.cpp','-o',out/'overnight_probes.exe'],'overnight_probe_compile')
        previous=run([out/'overnight_probes.exe','--audit-probes'],'overnight_audit_probes')
        current=run([out/'dispense_regressions.exe','--audit-probes'],'r2_audit_probes')
        if 'DIRECT_LAUNCH_36 state=SERVO_PULSE_OPEN opens=1' not in previous or 'MASKED_WINDOW_36 state=COMPLETE' not in previous:raise ValueError('baseline reproduction differs')
        if 'DIRECT_LAUNCH_36 state=FAULT opens=0' not in current or 'MASKED_WINDOW_36 state=FAULT reason=TARGET_OVERSHOOT' not in current:raise ValueError('R2 regression not fixed')
        result['native']=checks.collect_program_results(out,'.exe',run)
        text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o',
            'pythonpath='+str(HERE/'candidate')+' '+str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'),HERE/'tests/test_integration.py'],'backend_tests')
        result['backend_tests']=int(re.search(r'(\d+) passed',text).group(1))
        fe=HERE/'candidate/flutter'
        def flutter(args,name):
            q=subprocess.run([r'D:\dev\flutter\bin\flutter.bat']+args,cwd=fe,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240,env=env)
            (out/(name+'.log')).write_bytes(q.stdout);print(name+': '+('PASS' if q.returncode==0 else 'FAIL'),flush=True)
            if q.returncode:raise RuntimeError(name+' failed')
            return q.stdout.decode('utf-8','replace')
        flutter(['pub','get','--offline'],'flutter_pub')
        text=flutter(['test','--no-pub','--reporter','expanded','test/continuation_test.dart'],'flutter_tests')
        result['flutter_tests']=int(re.search(r'\+(\d+): All tests passed',text).group(1))
        flutter(['analyze','--no-pub'],'flutter_analyze');result['flutter_analyze']='PASS_NO_ISSUES'
        result['WINDOWS_OFFLINE_TEST_PASS']=True
    except Exception as e:
        result['WINDOWS_OFFLINE_TEST_PASS']=False;result['error']=str(e);raise
    finally:
        checks.write_json(out/'result.json',result)
    print(json.dumps({'output':str(out),**result},indent=2))
if __name__=='__main__':main()
