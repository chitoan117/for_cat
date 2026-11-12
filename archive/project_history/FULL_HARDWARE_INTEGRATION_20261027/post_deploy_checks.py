import asyncio,hashlib,json,os,subprocess,sys,urllib.request
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);pre=json.loads((E/'preflight_summary.json').read_text())
env={**os.environ,'PYTHONPATH':str(R/'jetson')+':'+str(R),'PYTHONDONTWRITEBYTECODE':'1','DATABASE_PATH':str(E/'post_test_isolated.db'),'ESP32_TRANSPORT':'MOCK','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','AI_SHADOW_MODE':'true'}
for k in ('FORCAT_FLUTTER_WEB_DIR','ESP32_BRIDGE_ENABLED','SCHEDULED_DRY_RUN_WORKER_ENABLED','SYSTEM_STATE_PROVIDER','FORCAT_TEST_PROJECT_ROOT','FORCAT_BRIDGE_TEST_BINARY'):env.pop(k,None)
commands=[]
for name,args in [('backend_post',[sys.executable,'-m','pytest','jetson/tests','-q','-ra']),('diff_check',['git','diff','--check']),('staged_diff_check',['git','diff','--cached','--check']),('pip_post',[sys.executable,'-m','pip','check'])]:
 p=subprocess.run(args,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=480);(E/(name+'.log')).write_bytes(p.stdout);commands.append({'name':name,'exit':p.returncode});assert p.returncode==0,p.stdout.decode()[-18000:]
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:return json.load(r)
s=get('/api/status');w=get('/api/meal-plans/worker')['worker']
assert s['data_source']=='REAL' and len(s['ultrasonic'])==4 and s['safety']['actuator_outputs_enabled']==0
assert all(s['safety'][k] is False for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution'))
assert w['running'] and w['enabled'] and w['last_error'] is None
assert hashlib.sha256((R/'.git/index').read_bytes()).hexdigest()==pre['index_sha256']
for name,meta in pre['ai_metadata'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==meta['sha256']
serial=subprocess.run(['fuser','/dev/ttyACM0'],capture_output=True);camera=subprocess.run(['fuser','/dev/video0'],capture_output=True)
assert len(serial.stdout.split())==1 and len(camera.stdout.split())==1
summary={'status':'RUNTIME_PASS','commands':commands,'ultrasonic':s['ultrasonic'],'safety':s['safety'],'worker':w,'serial_owner':serial.stdout.decode().strip(),'camera_owner':camera.stdout.decode().strip(),'index_preserved':True,'ai_unchanged':True}
(E/'post_deploy_checks.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
