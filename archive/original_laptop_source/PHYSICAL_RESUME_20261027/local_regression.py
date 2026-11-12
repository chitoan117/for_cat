import json,os,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=Path(r'D:\DA_KT_NC\feeder_demo')
sys.stdout.reconfigure(encoding='utf-8');results=[]
for name,args,cwd in (
 ('flutter_analyze',[r'D:\dev\flutter\bin\flutter.bat','analyze','--no-pub'],ROOT),
 ('flutter_tests',[r'D:\dev\flutter\bin\flutter.bat','test','--no-pub'],ROOT),
 ('js_regression',['node','--test','--test-reporter=tap',r'D:\for_cat\SCHEDULED_WORKER_20261026\web_regression_source\jetson\tests\web\feed_preview.test.cjs'],OUT),
):
 p=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 (OUT/(name+'.log')).write_bytes(p.stdout);results.append({'name':name,'exit':p.returncode});print(name+': '+str(p.returncode),flush=True)
 assert p.returncode==0,p.stdout.decode('utf-8','replace')
(OUT/'local_regression_result.json').write_text(json.dumps(results,indent=2))
