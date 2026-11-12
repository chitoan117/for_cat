"""Deploy only immutable REAL assets + backed-up 40 drop-in; existing API restart only."""
import asyncio,hashlib,json,os,shutil,sqlite3,subprocess,sys,tarfile,time,urllib.request
from pathlib import Path
ROOT=Path('/home/toan/for_cat');E=max((ROOT/'evidence').glob('physical_resume_20261027_*'),key=lambda p:p.name)
pre=json.loads((E/'preflight_summary.json').read_text());assert pre['backup_complete']
M=json.loads((E/'rc_real_sha256.json').read_text());assert M['mode']=='REAL'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'rc_real_only.tar.gz')==M['archive_sha256']
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:return r.status,r.read()
def jget(path):return json.loads(get(path)[1])
def safe(s):
 assert s['data_source']=='REAL' and s['esp32']['connected'] is True
 assert s['safety']['actuator_outputs_enabled']==0
 for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):assert s['safety'][k] is False
def hashes(folder):return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}
def backend_hashes():return {str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'jetson/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def pid(unit):return subprocess.check_output(['systemctl','--user','show',unit,'-p','MainPID','--value']).decode().strip()
safe(jget('/api/status'));beforeplans=jget('/api/meal-plans');beforecode=backend_hashes()
worker=jget('/api/meal-plans/worker')['worker'];assert worker['running'] is True and worker['last_error'] is None
beforepids={u:pid(u) for u in ('for-cat-api','for-cat-ai','for-cat-esp32-bridge')}
old=Path(pre['current_frontend']);oldassets=hashes(old)
diff={'added':[n for n in M['assets'] if n not in oldassets],'changed':[n for n in M['assets'] if n in oldassets and oldassets[n]!=M['assets'][n]],'removed':[n for n in oldassets if n not in M['assets']]}
(E/'frontend_asset_diff.json').write_text(json.dumps({'old_release':str(old),'rc':M,'differences':diff},indent=2))
new=ROOT/'.native-build/flutter/offline_rc_20261026_resume_20261027_r1';assert new.parent.is_dir() and not new.exists()
new.mkdir()
with tarfile.open(E/'rc_real_only.tar.gz','r:gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in M['assets'] and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
  target=new/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(member) as source,target.open('xb') as dest:shutil.copyfileobj(source,dest)
assert hashes(new)==M['assets']
sys.path.insert(0,str(ROOT/'jetson'));from app.frontend_assets import resolve_flutter_frontend
assert resolve_flutter_frontend(new)==new
drop=Path('/home/toan/.config/systemd/user/for-cat-api.service.d/40-flutter-real.conf')
original=drop.read_bytes();assert original.decode().count(str(old))==1
shutil.copy2(drop,E/'backup/40-flutter-real.conf.original')
newbody=original.decode().replace(str(old),str(new));tmp=drop.with_name('40-flutter-real.conf.physical-resume-tmp')
assert not tmp.exists();tmp.write_text(newbody);os.chmod(tmp,drop.stat().st_mode&0o777)
result={'status':'BLOCKED','evidence':str(E),'old_release':str(old),'new_release':str(new),'asset_diff_counts':{k:len(v) for k,v in diff.items()},'backend_changed':False,'actuator_commands':False}
try:
 os.replace(tmp,drop)
 subprocess.run(['systemctl','--user','daemon-reload'],check=True)
 subprocess.run(['systemctl','--user','restart','for-cat-api.service'],check=True,timeout=45)
 state=None
 for _ in range(60):
  try:
   state=jget('/api/status');safe(state)
   worker=jget('/api/meal-plans/worker')['worker']
   if worker['enabled'] is True and worker['running'] is True and worker['last_error'] is None:break
  except Exception:pass
  time.sleep(1)
 else:raise RuntimeError('API/worker did not recover')
 endpoints={}
 for path in ('/app','/kiosk','/diagnostics','/api/status','/api/meal-plans','/api/meal-plans/worker','/api/hx711/status','/api/hx711/calibration','/api/v1/esp32/status'):
  status,body=get(path);assert status==200
  endpoints[path]={'status':status,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
 assert get('/app')[1]==get('/kiosk')[1]
 assert hashlib.sha256(get('/flutter/main.dart.js')[1]).hexdigest()==M['assets']['main.dart.js']
 async def ws_check():
  import websockets
  async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
   frames=[json.loads(await asyncio.wait_for(ws.recv(),timeout=8)) for _ in range(3)]
  for frame in frames:safe(frame)
  return frames
 frames=asyncio.run(ws_check());(E/'post_deploy_ws.json').write_text(json.dumps(frames,indent=2))
 afterplans=jget('/api/meal-plans');assert afterplans['plans']==beforeplans['plans']
 assert {o['occurrence_id'] for o in beforeplans['recent_occurrences']} <= {o['occurrence_id'] for o in afterplans['recent_occurrences']}
 assert jget('/api/hx711/status')['actual_dispensed_grams'] is None
 assert backend_hashes()==beforecode
 assert sha(ROOT/'.git/index')==pre['index_sha256']
 for unit in ('for-cat-ai','for-cat-esp32-bridge'):assert pid(unit)==beforepids[unit]
 for name,meta in pre['ai_metadata'].items():assert sha(ROOT/name)==meta['sha256']
 with sqlite3.connect('file:'+pre['database']+'?mode=ro',uri=True) as db:
  counts={name:db.execute(sql).fetchone()[0] for name,sql in {'feed_requests':'SELECT COUNT(*) FROM feed_requests','feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
 assert counts==pre['baseline_feed_counts']
 result.update(status='RUNTIME_PASS',worker=worker,endpoints=endpoints,ws_frames=len(frames),plans_preserved=True,occurrences_preserved=True,index_preserved=True,ai_unchanged=True,backend_unchanged=True,feed_counts=counts,
  pids_before=beforepids,pids_after={u:pid(u) for u in beforepids},safety=state['safety'])
except Exception as error:
 result['error']=str(error)
 restore=drop.with_name('40-flutter-real.conf.rollback-tmp');restore.write_bytes(original);os.replace(restore,drop)
 subprocess.run(['systemctl','--user','daemon-reload'],check=True);subprocess.run(['systemctl','--user','restart','for-cat-api.service'],check=True,timeout=45)
 result['rollback']='PREVIOUS_FRONTEND_RESTORED';raise
finally:
 (E/'frontend_deploy_summary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
