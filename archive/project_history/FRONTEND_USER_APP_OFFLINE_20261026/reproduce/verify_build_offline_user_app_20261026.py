import subprocess,sys
import shutil
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(r'D:\DA_KT_NC\feeder_demo');OUT=Path(r'D:\for_cat\FRONTEND_USER_APP_OFFLINE_20261026');assert OUT.is_dir()
font=Path(r'D:\for_cat\HX711_CALIBRATION_20261026\web_real_hx711\assets\fonts\fallback\Roboto-Regular.ttf')
target=ROOT/'assets/fonts/Roboto-Regular.ttf';assert font.is_file();target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():shutil.copy2(font,target)
def run(label,args):
 p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
 (OUT/(label+'.log')).write_bytes(p.stdout);print(p.stdout.decode('utf-8','replace'),flush=True);assert p.returncode==0,label
run('dart_format',[r'D:\dev\flutter\bin\dart.bat','format','lib','test/user_app_offline_test.dart'])
run('flutter_analyze',[r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'])
run('flutter_tests',[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub'])
for mode in ('real','mock'):
 run('flutter_release_'+mode,[r'D:\dev\flutter\bin\flutter.bat','build','web','--release','--no-pub','--no-wasm-dry-run','--no-web-resources-cdn','--base-href=/flutter/','--dart-define=FEEDER_MODE='+mode,'--output='+str(OUT/('web_'+mode))])
