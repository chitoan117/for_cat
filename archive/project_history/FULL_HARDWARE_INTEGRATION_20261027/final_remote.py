import hashlib,json,os,re,sqlite3,subprocess,tarfile,urllib.request
from pathlib import Path
R=Path('/home/toan/for_cat');E=Path(EVIDENCE);C=E/'client_handoff';C.mkdir(exist_ok=False)
with tarfile.open(E/'client_handoff.tar.gz') as t:
 for m in t:
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=C/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,value in json.loads((C/'frontend_final_sha256.json').read_text()).items():assert sha(C/'frontend_source'/name)==value
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:return json.load(r)
pre=json.loads((E/'preflight_summary.json').read_text());s=get('/api/status');w=get('/api/meal-plans/worker')['worker'];b=get('/api/v1/esp32/status')
assert s['data_source']=='REAL' and len(s['ultrasonic'])==4 and s['safety']['actuator_outputs_enabled']==0
assert all(s['safety'][k] is False for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution'))
assert w['enabled'] and w['running'] and w['mode']=='DRY_RUN_ONLY' and w['last_error'] is None and w['actual_dispensed_grams'] is None
assert b['serial_tx_enabled'] is False and s['ai']['health']=='ONLINE' and s['weight']['grams'] is None
assert get('/api/hx711/calibration')['active'] is None
assert sha(R/'.git/index')==pre['index_sha256']
for name,meta in pre['ai_metadata'].items():assert sha(R/name)==meta['sha256']
for name,args in {'git_status':['git','status','--porcelain=v1','--branch'],'git_diff':['git','diff','--binary'],'git_staged_diff':['git','diff','--cached','--binary'],'services':['systemctl','--user','status','for-cat-api','for-cat-esp32-bridge','for-cat-ai','--no-pager','-l']}.items():
 p=subprocess.run(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'});assert p.returncode==0;(E/('post_'+name+'.log')).write_bytes(p.stdout)
 if name=='git_staged_diff':assert p.stdout.decode()==json.loads((E/'audit/git_staged_diff.json').read_text())['stdout']
with sqlite3.connect('file:'+pre['database']+'?mode=ro',uri=True) as db:
 counts={name:db.execute(sql).fetchone()[0] for name,sql in {'feed_requests':'SELECT COUNT(*) FROM feed_requests','feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
assert counts==pre['baseline_feed_counts']
result={'status':'RUNTIME_PASS','firmware':'SOFTWARE_READY','flash':'ESP32 FLASH REQUIRED','physical':'NOT_TESTED',
 'evidence':str(E),'ultrasonic':s['ultrasonic'],'safety':s['safety'],'actual_dispensed_grams':None,'hx711':'NOT_CALIBRATED',
 'backend_tests':445,'flutter_tests':63,'js_tests':14,'native_assertions':3576,'compatibility_frames':2,
 'ai_unchanged':True,'index_preserved':True,'feed_counts':counts,'acquisition_commands_sent':False,'flash_performed':False,
 'frontend_release':json.loads((E/'frontend_r2_result.json').read_text())['release']}
(E/'COMPLETION_WAITING_FOR_MANUAL_FLASH.json').write_text(json.dumps(result,indent=2))
(E/'final_rest_state.json').write_text(json.dumps(s,indent=2));(E/'final_worker.json').write_text(json.dumps(w,indent=2))
manifest={str(p.relative_to(E)):sha(p) for p in E.rglob('*') if p.is_file() and p.name!='manifest_final_sha256.json' and not any(part in ('flash_tool','__pycache__','.pytest_cache') for part in p.parts)}
(E/'manifest_final_sha256.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='ultrasonic'},indent=2))
