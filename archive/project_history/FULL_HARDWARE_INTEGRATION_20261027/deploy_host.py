import asyncio,hashlib,json,os,shutil,sqlite3,subprocess,sys,tarfile,time,urllib.request
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);M=json.loads((E/'release_manifest.json').read_text());pre=json.loads((E/'preflight_summary.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((E/'software_summary.json').read_text())['status']=='SOFTWARE_READY'
assert sha(E/'host_release.tar.gz')==M['archive_sha256']
for name,meta in M['files'].items():
 p=R/name;assert (sha(p) if p.exists() else None)==meta['before'],name+' changed since backup'
assert sha(R/'.git/index')==pre['index_sha256']
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:return r.read()
def jget(path):return json.loads(get(path))
def safe(s):
 assert s['data_source']=='REAL' and s['safety']['actuator_outputs_enabled']==0
 for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):assert s['safety'][k] is False
safe(jget('/api/status'));plans=jget('/api/meal-plans')['plans'];hx=jget('/api/hx711/calibration')
stage=E/'host_release';stage.mkdir()
with tarfile.open(E/'host_release.tar.gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=stage/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(m) as src,p.open('xb') as dst:shutil.copyfileobj(src,dst)
for name,meta in M['files'].items():assert sha(stage/'files'/name)==meta['after']
for name,value in M['web'].items():assert sha(stage/'web'/name)==value
for name,value in M['firmware'].items():assert sha(stage/'firmware'/name)==value
web=R/'.native-build/flutter/four_ultrasonic_20261027_r1';assert not web.exists();shutil.copytree(stage/'web',web)
sys.path.insert(0,str(R/'jetson'));from app.frontend_assets import resolve_flutter_frontend
assert resolve_flutter_frontend(web)==web
drop=Path('/home/toan/.config/systemd/user/for-cat-api.service.d/40-flutter-real.conf');body=drop.read_text();assert body.count(pre['current_frontend'])==1
backup=E/'deploy_backup';backup.mkdir();shutil.copy2(drop,backup/'40-flutter-real.conf')
for name in M['files']:
 p=R/name
 if p.exists():dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
oldbin=R/'.native-build/esp32/esp32_bridge';shutil.copy2(oldbin,backup/'esp32_bridge')
def install(source,target,mode=None):
 target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.u4_tmp');assert not temp.exists()
 shutil.copy2(source,temp)
 if mode is not None:os.chmod(temp,mode)
 os.replace(temp,target)
def service(*args):subprocess.run(['systemctl','--user',*args],check=True,timeout=45)
result={'status':'BLOCKED','evidence':str(E),'web':str(web),'manual_flash_required':True}
try:
 service('stop','for-cat-api.service');service('stop','for-cat-esp32-bridge.service')
 for name in M['files']:install(stage/'files'/name,R/name)
 install(E/'build/esp32_bridge',oldbin,0o755)
 tmp=E/'new_dropin.conf';tmp.write_text(body.replace(pre['current_frontend'],str(web)));install(tmp,drop)
 service('daemon-reload');service('start','for-cat-esp32-bridge.service');service('start','for-cat-api.service')
 for _ in range(60):
  try:
   state=jget('/api/status');safe(state);worker=jget('/api/meal-plans/worker')['worker']
   if state['esp32']['connected'] is True and worker['running']:break
  except Exception:pass
  time.sleep(1)
 else:raise RuntimeError('services not ready')
 assert len(state['ultrasonic'])==4
 for key in ('HC_SR04_2','JSN_SR04T_2'):
  assert state['ultrasonic'][key]['distance_cm'] is None and state['ultrasonic'][key]['wired'] is True and state['ultrasonic'][key]['state']=='UNKNOWN'
 assert worker['enabled'] and worker['mode']=='DRY_RUN_ONLY' and worker['last_error'] is None and worker['actual_dispensed_grams'] is None
 assert plans==jget('/api/meal-plans')['plans']
 assert hx==jget('/api/hx711/calibration')
 for url in ('/app','/kiosk','/diagnostics'):assert len(get(url))>100
 assert hashlib.sha256(get('/flutter/main.dart.js')).hexdigest()==M['web']['main.dart.js']
 async def frames():
  import websockets
  async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:return [json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(3)]
 ws=asyncio.run(frames());(E/'deployed_ws.json').write_text(json.dumps(ws,indent=2));assert all(len(s['ultrasonic'])==4 for s in ws)
 for name,meta in pre['ai_metadata'].items():assert sha(R/name)==meta['sha256']
 assert sha(R/'.git/index')==pre['index_sha256']
 with sqlite3.connect('file:'+pre['database']+'?mode=ro',uri=True) as db:
  counts={name:db.execute(sql).fetchone()[0] for name,sql in {'feed_requests':'SELECT COUNT(*) FROM feed_requests','feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
 assert counts==pre['baseline_feed_counts']
 result.update(status='RUNTIME_PASS',ultrasonic=state['ultrasonic'],safety=state['safety'],worker=worker,feed_counts=counts,calibration_unchanged=True,ai_unchanged=True,index_preserved=True,ws_frames=len(ws),deployed_files=list(M['files']))
except Exception as error:
 result['error']=str(error)
 service('stop','for-cat-api.service');service('stop','for-cat-esp32-bridge.service')
 for name in M['files']:
  if (backup/name).exists():install(backup/name,R/name)
 install(backup/'esp32_bridge',oldbin,0o755);install(backup/'40-flutter-real.conf',drop)
 service('daemon-reload');service('start','for-cat-esp32-bridge.service');service('start','for-cat-api.service')
 result['rollback']='RESTORED_OLD_EXISTING_FILES_AND_BIN';raise
finally:
 (E/'host_deploy_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
