"""Read-only real baseline, owner proof, bounded REST/WS observation; no serial/camera open."""
import asyncio,datetime,hashlib,json,os,sqlite3,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path('/home/toan/for_cat');E=max((ROOT/'evidence').glob('physical_resume_20261027_*'),key=lambda p:p.name)
before=json.loads((E/'preflight_summary.json').read_text());assert before['backup_complete'] and all(before['safety_checks'].values())
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as r:return json.load(r)
def safe(state):
 assert state['data_source']=='REAL' and state['esp32']['connected'] is True
 for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution'):assert state['safety'][k] is False,(k,state['safety'])
 assert state['safety']['actuator_outputs_enabled']==0
def owners(device):
 p=subprocess.run(['fuser',device],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
 return [int(s) for s in p.stdout.decode().split() if s.isdigit()]
def pid(unit):return int(subprocess.check_output(['systemctl','--user','show',unit,'-p','MainPID','--value']))
services={n:pid(n) for n in ('for-cat-api','for-cat-esp32-bridge','for-cat-ai')};serial=owners('/dev/ttyACM0');camera=owners('/dev/video0')
assert serial==[services['for-cat-esp32-bridge']],serial
detectors=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(b'\0')
  if args and args[0].decode(errors='replace')==str(ROOT/'jetson/ai/cat_dog_trt'):detectors.append(int(proc.name))
 except (OSError,PermissionError):pass
assert len(detectors)==1 and camera==detectors,(camera,detectors)
with sqlite3.connect('file:'+before['database']+'?mode=ro',uri=True) as db:
 sqlite={'quick_check':db.execute('PRAGMA quick_check').fetchone()[0],'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0]}
assert sqlite['quick_check']=='ok'
async def ws_check():
 import websockets
 frames=[]
 async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=6,max_size=131072) as ws:
  for _ in range(4):
   state=json.loads(await asyncio.wait_for(ws.recv(),timeout=7));safe(state);frames.append(state)
 return frames
ws_frames=asyncio.run(ws_check());(E/'baseline_ws_frames.json').write_text(json.dumps(ws_frames,indent=2))
samples=[]
for i in range(16):
 state=get('/api/status');safe(state);samples.append(state)
 if i<15:time.sleep(2)
(E/'baseline_rest_samples.json').write_text(json.dumps(samples,indent=2))
worker=get('/api/meal-plans/worker')['worker']
assert worker['enabled'] is True and worker['running'] is True and worker['mode']=='DRY_RUN_ONLY' and worker['timezone']=='Asia/Ho_Chi_Minh' and worker['last_error'] is None
assert all(s['ai']['health']=='ONLINE' and s['ai']['classification'] in ('CAT','DOG','NONE') for s in samples)
assert all(s['weight']['grams'] is None and s['weight']['calibration_state']=='NOT_CALIBRATED' for s in samples)
hx=get('/api/hx711/status');assert hx['actual_dispensed_grams'] is None and hx['actuator_execution'] is False
raw=[s['weight']['raw_counts'] for s in samples if s['weight']['raw_available'] is True]
first,last=samples[0]['esp32']['counters'],samples[-1]['esp32']['counters']
summary={'evidence':str(E),'status':'RUNTIME_PASS','services':services,'serial_owner':serial,'camera_owner':camera,'detector_pids':detectors,
 'sqlite':sqlite,'ws_frames':len(ws_frames),'rest_samples':len(samples),'worker':worker,'ai_classes_observed':sorted({s['ai']['classification'] for s in samples}),
 'safety':'DRY_RUN_PASS','actual_dispensed_grams':None,'hx711':{'state':'NOT_CALIBRATED','raw_available_samples':len(raw),'raw_min':min(raw),'raw_max':max(raw),'physical_load_test':'NOT_TESTED'},
 'ultrasonic':{k:samples[-1][k] for k in ('approach','water_operational')},
 'counter_deltas':{k:last[k]-first[k] for k in ('valid_reports','parse_errors','storage_errors','device_reboots')},
 'physical_tests':'NOT_TESTED','index_unchanged':hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==before['index_sha256']}
assert summary['counter_deltas']['storage_errors']==0
(E/'baseline_runtime_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
