"""Phase4 only: focused API/Flutter tests and offline REAL/MOCK web builds."""
from datetime import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'phase4'
FE=Path(r'D:\DA_KT_NC\feeder_demo')
BACKEND=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'
FLUTTER=Path(r'D:\dev\flutter\bin\flutter.bat')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,name,cwd=ROOT,timeout=240):
    p=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,timeout=timeout,
                     env={**os.environ,'FLUTTER_SUPPRESS_ANALYTICS':'true','PYTHONPATH':str(BACKEND)})
    (OUT/(name+'.log')).write_bytes(p.stdout+p.stderr)
    print(name+': '+('PASS' if p.returncode==0 else 'FAIL'),flush=True)
    if p.returncode:raise RuntimeError(name+' failed, see '+str(OUT/(name+'.log')))
    return p.stdout.decode('utf-8','replace')
def main():
    p=argparse.ArgumentParser();p.add_argument('part',choices=('backend','flutter','build'));args=p.parse_args()
    OUT.mkdir(exist_ok=True)
    result={'at':datetime.now().astimezone().isoformat(),'physical_pass':False,'part':args.part}
    if args.part=='backend':
        result['stdout']=run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider','-o',
            'pythonpath='+BACKEND.as_posix()+' '+ROOT.as_posix(),HERE/'test_phase4_api.py',
            HERE/'test_ai_contract.py',str(BACKEND/'tests/test_state_cache_resilience.py')+'::test_bad_ai_cache_never_becomes_fake_cat_or_none'],
            'backend_focused')
        result['api_fixture_sha256']=sha(OUT/'api_contract_fixture.json')
    elif args.part=='flutter':
        assert (OUT/'api_contract_fixture.json').is_file(),'Run backend export first'
        result['stdout']=run([FLUTTER,'test','--no-pub','--reporter','expanded',
            '--dart-define=FORCAT_PHASE4_FIXTURE='+str(OUT/'api_contract_fixture.json'),
            'test/production_phase4_test.dart','test/live_camera_test.dart','test/feeder_state_test.dart',
            'test/real_backend_test.dart','test/hx711_state_test.dart','test/mock_backend_test.dart'],
            'flutter_focused',FE)
        result['analyze']=run([FLUTTER,'analyze','--no-pub'],'flutter_analyze',FE)
    else:
        for mode in ('real','mock'):
            target=OUT/('web_'+mode)
            run([FLUTTER,'build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn',
                '--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(target)],'flutter_build_'+mode,FE,360)
            result[mode]={'main_dart_js_sha256':sha(target/'main.dart.js')}
        # Source + built artifacts must not contain production credentials or
        # private producer token contents. This uses an offline fixture sentinel.
        token=('SYNTHETIC_PHASE4_ONLY_'+'x'*40).encode()
        for root in (FE/'lib',OUT/'web_real',OUT/'web_mock'):
            for file in root.rglob('*'):
                if file.is_file():assert token not in file.read_bytes(),str(file)
        result['producer_secret_sentinel_absent']=True
        assert result['real']!=result['mock']
    (OUT/(args.part+'_result.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
