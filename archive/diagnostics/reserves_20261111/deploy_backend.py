from pathlib import Path
import hashlib,json,py_compile,shutil,sqlite3,subprocess,time,urllib.request
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson')
PLAN=json.loads((R/'backend_plan.json').read_text())
FILES={'main.py':ROOT/'app/main.py','system_state.py':ROOT/'app/system_state.py','reservoir_levels.py':ROOT/'app/reservoir_levels.py','reservoir_routes.py':ROOT/'app/api/reservoir_routes.py'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,p in FILES.items():
    assert (sha(p) if p.exists() else None)==PLAN[name]['before'],'Live source changed: '+name
    assert sha(R/'backend'/name)==PLAN[name]['after']
    py_compile.compile(str(R/'backend'/name),doraise=True)
CONFIG=ROOT/'data/reservoir_calibration.json'
candidate=json.loads((R/'reservoir_calibration.json').read_text())
assert candidate['schema_version']==1 and set(candidate['roles'])=={'food','water'}
assert all(v['source']=='OWNER_CONFIRMED_EMPTY_20261111' and v['full_cm'] is None for v in candidate['roles'].values())
assert not (R/'deployment_started').exists(),'Deployment already entered; inspect evidence before retrying'
BACKUP=R/'live_before';BACKUP.mkdir(exist_ok=True)
for name,p in FILES.items():
    if p.exists():shutil.copy2(p,BACKUP/name)
if CONFIG.exists():shutil.copy2(CONFIG,BACKUP/'reservoir_calibration.json')
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as r:return json.load(r)
def native():
    end=time.monotonic()+15
    while time.monotonic()<end:
        with sqlite3.connect(ROOT/'data/events.db',timeout=2) as db:s=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        if 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500:return s['telemetry']['fc_live']
        time.sleep(.25)
    raise RuntimeError('No fresh native telemetry; no deployment performed')
def service(action):subprocess.run(['systemctl','--user',action,'for-cat-api.service'],check=True,timeout=20)
before=native();(R/'native_before.json').write_text(json.dumps(before,indent=2))
old_state=get('/api/status');(R/'state_before.json').write_text(json.dumps(old_state,indent=2))
for role,key in [('food','HC_SR04_2'),('water','JSN_SR04T_2')]:
    channel=old_state['ultrasonic'][key]
    if channel['valid']:
        assert abs(channel['distance_cm']-candidate['roles'][role]['empty_cm'])<=1.0,'Container moved/filled since empty capture: '+role
(R/'deployment_started').write_text(str(time.time()))
service('stop')
try:
    for name,p in FILES.items():p.write_bytes((R/'backend'/name).read_bytes())
    temp=CONFIG.with_suffix('.json.new');temp.write_text(json.dumps(candidate,indent=2));temp.replace(CONFIG)
    service('start');deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        try:
            state=get('/api/status');water=get('/api/water-control')
            if state.get('esp32',{}).get('connected') and water.get('fresh') and water.get('enabled') is False and water.get('running') is False:
                if set(state.get('reservoirs',{}))=={'food','water'}:break
        except (OSError,ValueError):pass
        time.sleep(.3)
    else:raise RuntimeError('Fresh reserve and water state unavailable')
    for role in ('food','water'):
        if state['reservoirs'][role]['valid']:
            assert state[role+'_reservoir_percent']==0,(role,state['reservoirs'][role])
        else:assert state[role+'_reservoir_percent'] is None,'Never show fake zero without sensor data'
        assert state['reservoirs'][role]['calibration']=='EMPTY_ONLY'
    after=native()
    for key in ('tare_counts','grams_per_count','backup_enabled','demo_exited'):assert before[key]==after[key],key
    for unit in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service'):
        subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True)
    result={'deployed':True,'reserve_levels':state['reservoirs'],'water_control':water,'native_calibration_and_modes_preserved':True,'firmware_not_flashed_by_this_backend_script':True,'bridge_not_changed_by_this_backend_script':True,'pump_enable_sent':False,'full_reference_not_invented':True,'live_empty_check_pending':not all(v['valid'] for v in state['reservoirs'].values()),'hashes':PLAN}
    (R/'backend_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
except BaseException:
    service('stop')
    for name,p in FILES.items():
        if (BACKUP/name).exists():p.write_bytes((BACKUP/name).read_bytes())
        elif PLAN[name]['before'] is None:p.unlink(missing_ok=True)
    if (BACKUP/'reservoir_calibration.json').exists():CONFIG.write_bytes((BACKUP/'reservoir_calibration.json').read_bytes())
    else:CONFIG.unlink(missing_ok=True)
    service('start');raise
