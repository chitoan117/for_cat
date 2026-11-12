"""Only updated REAL/MOCK camera-capable releases; WEB_FINAL artifacts untouched."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
OUT=Path(__file__).resolve().parent;FE=Path(r'D:\DA_KT_NC\feeder_demo')
result={}
def run(args,name):
    p=subprocess.run(args,cwd=FE,env={**os.environ,'FLUTTER_SUPPRESS_ANALYTICS':'true'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (OUT/(name+'.log')).write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(p.stdout.decode('utf-8','replace'))
    print(name+': PASS',flush=True)
for mode in ('real','mock'):
    target=OUT/('web_'+mode)
    run([r'D:\dev\flutter\bin\flutter.bat','build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn',
         '--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(target)],'flutter_build_'+mode)
    marker={'mode':mode.upper(),'base_href':'/flutter/','target_grams':35,'actuator_execution':False,
            'actual_dispensed_grams':None,'scope':'LIVE_CAMERA_OFFLINE_PREPARATION_NOT_DEPLOYED'}
    (target/'forcat_build.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
    assert (target/'canvaskit').is_dir()
    result[mode]={'main_dart_js_sha256':hashlib.sha256((target/'main.dart.js').read_bytes()).hexdigest()}
assert result['real']!=result['mock']
(OUT/'flutter_build_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
