import json,subprocess,sys,tarfile,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=Path(r'D:\DA_KT_NC\feeder_demo');C=json.loads((O/'connection.json').read_text());sys.stdout.reconfigure(encoding='utf-8')
def run(name,args):
 r=subprocess.run(args,cwd=P,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240);(O/(name+'.log')).write_bytes(r.stdout);print(name+':'+str(r.returncode));assert r.returncode==0,r.stdout.decode('utf-8','replace')
run('dart_format',[r'D:\dev\flutter\bin\dart.bat','format','lib/diagnostic_models.dart','test/ultrasonic_real_test.dart'])
run('flutter_analyze',[r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub']);run('flutter_tests',[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub'])
for mode in ('real','mock'):
 run('flutter_build_'+mode,[r'D:\dev\flutter\bin\flutter.bat','build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn','--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(O/('web_'+mode))])
 (O/('web_'+mode)/'forcat_build.json').write_text(json.dumps({'mode':mode.upper(),'base_href':'/flutter/','target_grams':35,'actuator_execution':False,'actual_dispensed_grams':None,'features':['ULTRASONIC4_V1','OFFLINE_PIN_METADATA_FIX'],'flutter_tests':63},indent=2))
assets={p.relative_to(O/'web_real').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (O/'web_real').rglob('*') if p.is_file()}
(O/'frontend_r2_sha256.json').write_text(json.dumps(assets,indent=2))
with tarfile.open(O/'frontend_r2.tar.gz','w:gz') as t:
 for name in assets:t.add(O/'web_real'/name,arcname=name)
for f in ('frontend_r2.tar.gz','frontend_r2_sha256.json'):
 r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(O/f),'toan@'+C['host']+':'+C['evidence']+'/'+f],capture_output=True,timeout=120);assert r.returncode==0,r.stderr.decode()
