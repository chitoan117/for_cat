"""Flutter-only, offline final checks. No Jetson/backend/API/browser requests."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path

ROOT=Path(r'D:\DA_KT_NC\feeder_demo')
OUT=Path(__file__).resolve().parent
assert ROOT.is_dir() and OUT.is_dir()
sys.stdout.reconfigure(encoding='utf-8')
flutter=r'D:\dev\flutter\bin\flutter.bat'
checks={}
def run(name,args):
    result=subprocess.run(args,cwd=ROOT,env={**os.environ,'FLUTTER_SUPPRESS_ANALYTICS':'true'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (OUT/(name+'.log')).write_bytes(result.stdout)
    checks[name]={'exit_code':result.returncode,'args':args}
    print(f'{name}: '+('PASS' if result.returncode==0 else 'FAIL'),flush=True)
    if result.returncode!=0:raise RuntimeError(name+' failed: '+result.stdout.decode('utf-8','replace')[-5000:])
    return result.stdout.decode('utf-8','replace')

try:
    text=run('analyze',[flutter,'analyze','--no-pub'])
    assert 'No issues found!' in text
    text=run('tests',[flutter,'test','--no-pub'])
    count=re.search(r'\+(\d+): All tests passed!',text)
    if not count:raise RuntimeError('Cannot confirm Flutter test count')
    checks['tests']['passed']=int(count.group(1))
    for mode in ('real','mock'):
        web=OUT/('web_'+mode)
        run('build_'+mode,[flutter,'build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn','--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(web)])
        assert '<base href="/flutter/">' in (web/'index.html').read_text(encoding='utf-8')
        assert (web/'canvaskit').is_dir() and (web/'assets/assets/fonts/Roboto-Regular.ttf').is_file()
        marker={'mode':mode.upper(),'base_href':'/flutter/','target_grams':35,'actuator_execution':False,
                'actual_dispensed_grams':None,'scope':'WEB_FINAL_OFFLINE_NOT_DEPLOYED',
                'flutter_tests_passed':checks['tests']['passed']}
        (web/'forcat_build.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
        checks['build_'+mode]['main_dart_js_sha256']=hashlib.sha256((web/'main.dart.js').read_bytes()).hexdigest()
    assert checks['build_real']['main_dart_js_sha256']!=checks['build_mock']['main_dart_js_sha256']
    checks['mode_separation']='PASS'
    checks['external_runtime_asset_configuration']='LOCAL_CANVASKIT_AND_FONT_NO_WEB_RESOURCES_CDN'
    checks['backend_changed']=False
    checks['status']='PASS'
finally:
    (OUT/'result.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'status':checks['status'],'flutter_tests':checks['tests']['passed'],'real_mock_separate':checks['mode_separation']},indent=2))
