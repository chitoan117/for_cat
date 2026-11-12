"""Focused new-only Windows C++/ASGI/Flutter checks; no real device or server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe';PY=sys.executable
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(argv,name,cwd=HERE):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8','FLUTTER_SUPPRESS_ANALYTICS':'true'})
    (HERE/'evidence'/(name+'.log')).write_bytes(p.stdout)
    print(name+': '+('PASS' if p.returncode==0 else 'FAIL'),flush=True)
    if p.returncode:raise RuntimeError(name+' failed; read evidence log')
    return p.stdout.decode('utf-8','replace')
def main():
    p=argparse.ArgumentParser();p.add_argument('--part',choices=('all','native','timeline','backend','flutter'),default='all');p.add_argument('--case');a=p.parse_args()
    locked=json.loads((HERE/'SOURCE_BASELINE.json').read_text())
    assert all(sha(Path(v['source']))==v['sha256'] for v in locked.values()),'qualified input changed'
    result=json.loads((HERE/'result.json').read_text()) if (HERE/'result.json').exists() else {}
    out=HERE/'native';out.mkdir(exist_ok=True)
    if a.part in ('all','native'):
        common=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE/'candidate/bridge')]
        for label,headers in [('baseline',KIT/'firmware/include'),('candidate',HERE/'candidate/firmware/include')]:
            run(common+['-I'+str(headers),HERE/'tests/logic_tests.cpp','-o',out/(label+'.exe')],label+'_compile')
            probe=run([out/(label+'.exe'),'--overshoot-probe'],label+'_overshoot_probe')
            assert ('state=COMPLETE' in probe if label=='baseline' else 'state=FAULT reason=TARGET_OVERSHOOT' in probe)
        text=run([out/'candidate.exe'],'logic_tests')
        group,checks=map(int,re.search(r'OFFLINE_LOGIC_PASS groups=(\d+) checks=(\d+)',text).groups())
        outcomes=[json.loads(line[len('SIM_FEED_RESULT '):]) for line in text.splitlines() if line.startswith('SIM_FEED_RESULT ')]
        (HERE/'fixtures/dispense_outcomes.json').write_text(json.dumps({v['scenario']:v for v in outcomes},indent=2)+'\n')
        result.update(native_groups=group,native_checks=checks,overshoot_regression='REPRODUCED_BASELINE_COMPLETE_FIXED_CANDIDATE_FAULT')
    if a.part in ('all','timeline'):
        common=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE/'candidate/bridge'),
                '-I'+str(KIT/'web_hardware/native_jsonc_install/include')]
        run(common+[HERE/'tests/timeline_probe.cpp',KIT/'web_hardware/native_jsonc_install/lib/libjson-c.a','-ladvapi32','-o',out/'timeline.exe'],'timeline_compile')
        text=run([out/'timeline.exe',HERE/'fixtures/synthetic_wire.jsonl'],'timeline_probe')
        rows=[json.loads(x) for x in text.splitlines()]
        assert len(rows)==6
        (HERE/'fixtures/session_timeline.json').write_text(json.dumps(rows,indent=2)+'\n')
        result['new_timeline_cases']=6
    if a.part in ('all','backend'):
        selection=str(HERE/'tests/test_integration.py')+('::'+a.case if a.case else '')
        text=run([PY,'-B','-m','pytest','-q','-p','no:cacheprovider','-o','pythonpath='+str(HERE/'candidate')+' '+str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'),selection],'backend_'+(a.case or 'tests'))
        result['backend_'+(a.case or 'tests')]=int(re.search(r'(\d+) passed',text).group(1))
    if a.part in ('all','flutter'):
        fe=HERE/'candidate/flutter'
        run([r'D:\dev\flutter\bin\flutter.bat','pub','get','--offline'],'flutter_pub',fe)
        command=[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub','--reporter','expanded','test/continuation_test.dart']
        if a.case:
            # Windows .bat dispatch interprets unquoted | as a pipeline. Each
            # selector is passed independently; never forward shell metacharacters.
            total=0
            for n,selector in enumerate(a.case.split('|')):
                if not re.fullmatch(r'[A-Za-z0-9_/]+',selector):raise ValueError('simple Flutter selector required')
                text=run(command+['--name',selector],'flutter_selected_'+str(n),fe)
                total+=int(re.search(r'\+(\d+): All tests passed',text).group(1))
            result['flutter_selected']=total
        else:
            text=run(command,'flutter_tests',fe)
            result['flutter_tests']=int(re.search(r'\+(\d+): All tests passed',text).group(1))
        run([r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'],'flutter_analyze',fe)
        result['flutter_analyze']='PASS_NO_ISSUES'
    result.update(scope='WINDOWS_OFFLINE_SIMULATION_ONLY',physical_pass=False,ARM64_candidate='NOT_RUN',
        serial_opened=False,camera_opened=False,services_changed=False,production_or_locked_inputs_changed=False)
    (HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert all(sha(Path(v['source']))==v['sha256'] for v in locked.values())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
