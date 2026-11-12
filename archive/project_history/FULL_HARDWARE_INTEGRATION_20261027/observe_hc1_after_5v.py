"""Passive re-observation after owner restored sensor 5V; no serial open/TX/restart."""
import asyncio,datetime,hashlib,json,math,statistics,subprocess,time,urllib.request
from pathlib import Path
E=Path(EVIDENCE);HC='HC_SR04_1'
O=E/('hc1_after_sensor_5v_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));O.mkdir()
correction={'source':'OWNER_MESSAGE_AND_TWO_PHOTOS','sensor_supply_nominal_v':5,
 'common_ground':'OWNER_CONFIRMED_WITH_ESP32','previous_capture':str(E/'hc1_target_40cm_20261027T043102218148Z'),
 'previous_capture_condition':'OWNER_REPORTS_SENSOR_5V_WAS_NOT_CONNECTED',
 'interpretation':'Previous TIMEOUT evidence retained; not proof of sensor failure',
 'voltage_measured':False,'photos_are_not_an_electrical_verification':True}
(O/'owner_power_correction.json').write_text(json.dumps(correction,indent=2))
result={'status':'BLOCKED','evidence':str(O),'serial_opened':False,'commands_sent':[],
 'service_restarts':False,'physical_status':'NOT_TESTED','reference_target_cm':40,
 'reference_source':'PREVIOUS_OWNER_TARGET_PLACEMENT_APPROXIMATE_NOT_MEASURED_BY_AGENT'}
states=[];samples=[]
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as r:return json.load(r)
def check(state):
 assert state['data_source']=='REAL' and state['esp32']['connected'] is True
 assert state['safety']['actuator_outputs_enabled']==0
 for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution'):assert state['safety'][k] is False
 assert state['ultrasonic'][HC]['firmware_supported'] is True
 assert state['ultrasonic'][HC]['enabled'] is True,'HC1 no longer enabled after power change; need inspect before retry'
 for key,s in state['ultrasonic'].items():
  if key!=HC:assert s['enabled'] is False and s['distance_cm'] is None
try:
 first=get('/api/status');check(first);seen=set();deadline=time.monotonic()+65
 while len(samples)<24 and time.monotonic()<deadline:
  state=get('/api/status');check(state);states.append(state);s=state['ultrasonic'][HC]
  stamp=s['last_update']
  if stamp is not None and stamp not in seen:
   seen.add(stamp);samples.append({'observed_at':state['observed_at'],'esp32_monotonic_ms':state['esp32']['monotonic_ms'],**s})
  if len(samples)<24:time.sleep(1.1)
 assert len(samples)>=20,'Not enough independent completed updates'
 valid=[s['distance_cm'] for s in samples if s['valid'] is True and s['state']=='HEALTHY' and s['distance_cm'] is not None]
 assert all(type(v) in (int,float) and math.isfinite(v) and 0<v<=400 for v in valid)
 async def frames():
  import websockets
  async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
   values=[json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(4)]
  for state in values:check(state)
  return values
 ws=asyncio.run(frames());(O/'ws_frames.json').write_text(json.dumps(ws,indent=2))
 final=get('/api/status');check(final)
 worker=get('/api/meal-plans/worker')['worker'];assert worker['running'] and worker['last_error'] is None and worker['actual_dispensed_grams'] is None
 assert get('/api/hx711/status')['actual_dispensed_grams'] is None
 owner=subprocess.run(['fuser','/dev/ttyACM0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 pid=int(subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge','-p','MainPID','--value']))
 assert [int(p) for p in owner.stdout.split()]==[pid]
 metrics={'independent_updates':len(samples),'valid_samples':len(valid),
  'timeout_reports':sum(s['timeout'] is True for s in samples),'stale_reports':sum(s['stale'] is True for s in samples),
  'states':sorted({s['state'] for s in samples}),'timeout_counter_delta':samples[-1]['timeout_count']-samples[0]['timeout_count'],
  'minimum_cm':min(valid) if valid else None,'maximum_cm':max(valid) if valid else None,
  'mean_cm':statistics.mean(valid) if valid else None,'median_cm':statistics.median(valid) if valid else None,
  'spread_cm':max(valid)-min(valid) if valid else None,'stddev_cm':statistics.pstdev(valid) if valid else None,
  'max_sample_age_ms':max((s['sample_age_ms'] for s in samples if s['sample_age_ms'] is not None),default=None)}
 if valid:metrics['mean_minus_nominal_target_cm']=statistics.mean(valid)-40
 result.update(status='RUNTIME_PASS' if len(valid)>=20 else 'TIMEOUT' if not valid and metrics['timeout_reports'] else 'BLOCKED',
  metrics=metrics,other_channels_disabled=True,rest_ws_verified=True,safety=final['safety'],actual_dispensed_grams=None,
  worker_running=True,serial_owner=pid,near_far_response='NOT_TESTED')
 (O/'final_state.json').write_text(json.dumps(final,indent=2))
except Exception as error:
 result['error']=str(error);raise
finally:
 (O/'rest_full_states.json').write_text(json.dumps(states,indent=2));(O/'samples.json').write_text(json.dumps(samples,indent=2))
 (O/'summary.json').write_text(json.dumps(result,indent=2))
 (O/'manifest_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2))
 print(json.dumps(result,indent=2))
