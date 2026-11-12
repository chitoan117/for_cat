"""Owner positioned HC1 target at nominal20cm. Passive REST/WS only, no commands."""
import asyncio,datetime,hashlib,json,math,statistics,subprocess,time,urllib.request
from pathlib import Path
E=Path(EVIDENCE);HC='HC_SR04_1';TARGET_CM=20
BASE=E/'hc1_after_sensor_5v_20261027T043932670884Z/summary.json'
O=E/('hc1_target_20cm_passive_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));O.mkdir()
result={'status':'BLOCKED','evidence':str(O),'operator_declared_target_cm':TARGET_CM,
 'reference':'USER_POSITIONED_FLAT_TARGET_APPROXIMATE_DISTANCE','serial_opened':False,'commands_sent':[],
 'service_restarts':False,'physical_status':'NOT_TESTED','settle_seconds':3,'baseline_evidence':str(BASE)}
states=[];samples=[]
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as r:return json.load(r)
def check(s):
 assert s['data_source']=='REAL' and s['esp32']['connected'] is True
 assert s['safety']['actuator_outputs_enabled']==0
 for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):assert s['safety'][k] is False
 row=s['ultrasonic'][HC]
 assert row['enabled'] is True and row['firmware_supported'] is True
 assert (row['trigger_gpio'],row['echo_gpio'],row['role'])==(12,13,'CAT_APPROACH')
 for key,row in s['ultrasonic'].items():
  if key!=HC:assert row['enabled'] is False and row['distance_cm'] is None
try:
 baseline=json.loads(BASE.read_text());assert baseline['metrics']['valid_samples']>=20
 before=get('/api/status');check(before);(O/'before_state.json').write_text(json.dumps(before,indent=2));time.sleep(3)
 seen=set();deadline=time.monotonic()+65
 while len(samples)<24 and time.monotonic()<deadline:
  s=get('/api/status');check(s);states.append(s);row=s['ultrasonic'][HC];stamp=row['last_update']
  if stamp is not None and stamp not in seen:
   seen.add(stamp);samples.append({'observed_at':s['observed_at'],'esp32_monotonic_ms':s['esp32']['monotonic_ms'],**row})
  if len(samples)<24:time.sleep(1.1)
 assert len(samples)>=20,'Insufficient independent updates'
 valid=[row['distance_cm'] for row in samples if row['valid'] is True and row['state']=='HEALTHY' and row['distance_cm'] is not None]
 assert all(type(v) in (int,float) and math.isfinite(v) and 0<v<=400 for v in valid)
 async def ws_frames():
  import websockets
  async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
   frames=[json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(4)]
  for frame in frames:check(frame)
  return frames
 ws=asyncio.run(ws_frames());(O/'ws_frames.json').write_text(json.dumps(ws,indent=2))
 final=get('/api/status');check(final);worker=get('/api/meal-plans/worker')['worker']
 assert worker['enabled'] and worker['running'] and worker['last_error'] is None and worker['actual_dispensed_grams'] is None
 assert get('/api/hx711/status')['actual_dispensed_grams'] is None
 owner=subprocess.run(['fuser','/dev/ttyACM0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 bridge_pid=int(subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge','-p','MainPID','--value']))
 assert [int(v) for v in owner.stdout.split()]==[bridge_pid]
 metrics={'independent_updates':len(samples),'valid_samples':len(valid),'timeout_reports':sum(row['timeout'] is True for row in samples),
  'stale_reports':sum(row['stale'] is True for row in samples),'states':sorted({row['state'] for row in samples}),
  'timeout_counter_delta':samples[-1]['timeout_count']-samples[0]['timeout_count'],
  'minimum_cm':min(valid) if valid else None,'maximum_cm':max(valid) if valid else None,
  'mean_cm':statistics.mean(valid) if valid else None,'median_cm':statistics.median(valid) if valid else None,
  'spread_cm':max(valid)-min(valid) if valid else None,'stddev_cm':statistics.pstdev(valid) if valid else None,
  'max_sample_age_ms':max((row['sample_age_ms'] for row in samples if row['sample_age_ms'] is not None),default=None)}
 comparison={'baseline_target_cm':40,'baseline_mean_cm':baseline['metrics']['mean_cm'],'expected_direction':'DECREASE'}
 if valid:
  comparison.update(mean_change_cm=metrics['mean_cm']-baseline['metrics']['mean_cm'],
    direction_correct=metrics['mean_cm']<baseline['metrics']['mean_cm'],
    sample_ranges_separated=max(valid)<baseline['metrics']['minimum_cm'])
 result.update(status='RUNTIME_PASS' if len(valid)>=20 else 'TIMEOUT' if not valid and metrics['timeout_reports'] else 'BLOCKED',
  metrics=metrics,comparison=comparison,other_channels_disabled=True,rest_ws_verified=True,serial_owner=bridge_pid,
  safety=final['safety'],actual_dispensed_grams=None,worker_running=True,far_response='NOT_TESTED')
 (O/'final_state.json').write_text(json.dumps(final,indent=2))
except Exception as error:
 result['error']=str(error);raise
finally:
 (O/'rest_full_states.json').write_text(json.dumps(states,indent=2));(O/'samples.json').write_text(json.dumps(samples,indent=2))
 (O/'summary.json').write_text(json.dumps(result,indent=2))
 (O/'manifest_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2))
 print(json.dumps(result,indent=2))
