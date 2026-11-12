import hashlib,json,subprocess,sys
from pathlib import Path
O=Path(__file__).resolve().parent;P=Path(r'D:\DA_KT_NC\feeder_demo');sys.stdout.reconfigure(encoding='utf-8')
def run(name,args,cwd=P):
 r=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=360);(O/(name+'.log')).write_bytes(r.stdout);print(name+': '+str(r.returncode),flush=True)
 assert r.returncode==0,r.stdout.decode('utf-8','replace')
run('dart_format',[r'D:\dev\flutter\bin\dart.bat','format','lib/diagnostic_models.dart','lib/diagnostics_page.dart','test/ultrasonic_real_test.dart'])
run('flutter_analyze',[r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'])
run('flutter_tests',[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub'])
run('js_regression',['node','--test','--test-reporter=tap',str(O/'payload/jetson/tests/web/feed_preview.test.cjs')],O)
run('firmware_build',[r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',str(O/'firmware/esp32'),'-e','diag_four_ultrasonic','-e','diag_current_hardware'],O)
for mode in ('real','mock'):
 run('flutter_build_'+mode,[r'D:\dev\flutter\bin\flutter.bat','build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn','--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(O/('web_'+mode))])
 marker={'mode':mode.upper(),'base_href':'/flutter/','target_grams':35,'actuator_execution':False,'actual_dispensed_grams':None,'features':['ULTRASONIC4_V1','MANUAL_SCHEDULED_DRY_RUN','HX711_READINESS_ONLY']}
 (O/('web_'+mode)/'forcat_build.json').write_text(json.dumps(marker,indent=2))
