"""Final read-only production verification + evidence manifests; no sensor TX."""
import datetime,hashlib,json,sqlite3,statistics,subprocess,tarfile,urllib.request
from pathlib import Path
R=Path('/home/toan/for_cat');E=max((R/'evidence').glob('physical_resume_20261027_*'),key=lambda p:p.name);C=E/'client_evidence';C.mkdir(exist_ok=False)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
with tarfile.open(E/'client_evidence.tar.gz','r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
  p=C/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with tar.extractfile(m) as src,p.open('xb') as dst:dst.write(src.read())
for name,value in json.loads((C/'client_manifest_sha256.json').read_text()).items():assert sha(C/name)==value
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:return json.load(r)
pre=json.loads((E/'preflight_summary.json').read_text());state=get('/api/status');worker=get('/api/meal-plans/worker');bridge=get('/api/v1/esp32/status');hx=get('/api/hx711/status');cal=get('/api/hx711/calibration')
for name,body in {'status':state,'worker':worker,'bridge':bridge,'hx_status':hx,'calibration':cal}.items():(E/('final_'+name+'.json')).write_text(json.dumps(body,indent=2))
assert state['data_source']=='REAL' and state['esp32']['connected'] is True
for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):assert state['safety'][k] is False
assert state['safety']['actuator_outputs_enabled']==0 and hx['actual_dispensed_grams'] is None
assert worker['worker']['enabled'] and worker['worker']['running'] and worker['worker']['mode']=='DRY_RUN_ONLY' and worker['worker']['last_error'] is None
assert state['ai']['health']=='ONLINE' and state['ai']['classification'] in ('CAT','DOG','NONE')
assert state['weight']['grams'] is None and state['weight']['calibration_state']=='NOT_CALIBRATED' and cal['active'] is None
assert bridge['serial_tx_enabled'] is False and bridge['unsafe_telemetry_latched'] is False
index=sha(R/'.git/index');assert index==pre['index_sha256']
git={}
for name,args in {'git_diff':['git','diff','--binary'],'git_staged_diff':['git','diff','--cached','--binary'],'git_status':['git','status','--porcelain=v1','--branch']}.items():
 p=subprocess.run(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20);assert p.returncode==0
 original=json.loads((E/'audit'/(name+'.json')).read_text())
 assert p.stdout.decode()==original['stdout'],name+' changed unexpectedly'
 git[name]='UNCHANGED';(E/('final_'+name+'.log')).write_bytes(p.stdout)
for name,meta in pre['ai_metadata'].items():assert sha(R/name)==meta['sha256']
with sqlite3.connect('file:'+pre['database']+'?mode=ro',uri=True) as db:
 counts={name:db.execute(sql).fetchone()[0] for name,sql in {'feed_requests':'SELECT COUNT(*) FROM feed_requests','feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
assert counts==pre['baseline_feed_counts']
rows=json.loads((E/'baseline_rest_samples.json').read_text());raw=[s['weight']['raw_counts'] for s in rows if s['weight']['raw_available']]
raw_summary={'source':'PASSIVE_REAL_TELEMETRY_UNKNOWN_LOAD_NOT_CALIBRATION','samples':len(raw),'expected_grams':None,'raw_mean':statistics.mean(raw),'raw_min':min(raw),'raw_max':max(raw),'spread_counts':max(raw)-min(raw),
 'stable':'UNKNOWN','measured_grams':None,'error_grams':None,'error_percent':None,'physical_load_response':'NOT_TESTED'}
(E/'hx711_precalibration_raw_summary.json').write_text(json.dumps(raw_summary,indent=2))
checks=json.loads((E/'regression/summary.json').read_text());candidate=json.loads((E/'firmware_candidate_r2/software_test_summary.json').read_text());browser=json.loads((C/'browser_runtime_summary.json').read_text())
assert checks['status']=='SOFTWARE_READY' and candidate['status']=='SOFTWARE_READY' and browser['status']=='RUNTIME_PASS'
service=subprocess.run(['systemctl','--user','status','for-cat-api','for-cat-esp32-bridge','for-cat-ai','--no-pager','-l'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20);assert service.returncode==0
(E/'final_services.log').write_bytes(service.stdout)
result={'status':'RUNTIME_PASS','physical_progress':'BLOCKED','reason':'USER_WIRING_CONFIRMATION_AND_LEGACY_RTC_PIN_ISOLATION_REQUIRED',
 'evidence':str(E),'frontend':'RUNTIME_PASS','backend_tests':checks['backend_passed'],'flutter_tests':54,'js_tests':14,'cpp_assertions_checks':3556,'cpp_compatibility_frames':2,'browser_real_screenshots':len(browser['screens']),
 'safety':state['safety'],'actual_dispensed_grams':None,'hx711_calibration':'NOT_CALIBRATED','hx_raw':raw_summary,'firmware_candidate':'SOFTWARE_READY','firmware_flash':'NOT_TESTED',
 'git_preserved':git,'index_sha256':index,'ai_unchanged':True,'feed_counts':counts,'serial_tx_sent':False,
 'next_user_action':'Power off ESP32 and isolate #2 from GPIO16/17/18/10 before reconnect; no actuator power.'}
(E/'completion_partial_physical_blocked.json').write_text(json.dumps(result,indent=2))
manifest={str(p.relative_to(E)):sha(p) for p in E.rglob('*') if p.is_file() and p.name!='manifest_final_sha256.json' and '.pytest_cache' not in p.parts}
(E/'manifest_final_sha256.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(result,indent=2))
