"""Read-only audit of failed independent verify5; no serial, tare, model activation."""
import datetime,hashlib,json,statistics,urllib.request
from pathlib import Path
E=Path(EVIDENCE);S=E/'fast_track_ultrasonic';session_id='hxcal_e721ec976ad44342b4522a051ba6c9f1'
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as response:return json.load(response)
cal=get('/api/hx711/calibration');state=get('/api/status');worker=get('/api/meal-plans/worker')['worker']
assert cal['active'] is None and cal['latest_session']['session_id']==session_id
assert state['data_source']=='REAL' and state['esp32']['connected'] is True and state['weight']['grams'] is None
assert state['safety']['actuator_outputs_enabled']==0
for key in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'):assert state['safety'][key] is False
assert all(not row['enabled'] for row in state['ultrasonic'].values())
assert worker['actuator_execution'] is False and worker['actual_dispensed_grams'] is None
point_ids={'fit0':'9767b450ae924da6a5baead5a2b088fa','fit5':'915b21bd0b0e4f5a8c0454098657379e','verify0':'437030a123404af5914331d78390fc26','verify5':'fb0d234c424c4eea9f7dba6775252ba0','verify0_after_failed5':'3340e334213d4d59950296108b43525f'}
points={name:json.loads((S/session_id/(pid+'.point.json')).read_text()) for name,pid in point_ids.items()}
for name,p in points.items():assert p['session_id']==session_id and p['point_id']==point_ids[name]
model=cal['latest_session']['candidate'];factor=model['grams_per_count'];offset=model['tare_offset_counts']
stats={name:{'reference_g':p['mass_g'],'captured_at':p['captured_at'],'host_boot_id':p['host_boot_id'],'boot_estimate_ms':p['boot_estimate_ms'],
  'mean_raw':p['stats']['mean_raw'],'spread_counts':p['stats']['spread_counts'],
  'candidate_grams':(p['stats']['mean_raw']-offset)*factor,'point_id':p['point_id']} for name,p in points.items()}
verify_delta=(stats['verify5']['mean_raw']-stats['verify0']['mean_raw'])*factor
new_zero=stats['verify0_after_failed5']['candidate_grams']
shift_from_first_zero=new_zero-stats['verify0']['candidate_grams']
new_boot_relative_load=stats['verify5']['candidate_grams']-new_zero
report={'status':'BLOCKED','reason':'INDEPENDENT_VERIFY5_ERROR_EXCEEDS_TOLERANCE',
 'candidate_active':False,'session_id':session_id,'model_digest':cal['latest_session']['candidate_digest'],
 'reference_declared_g':5,'candidate_grams':stats['verify5']['candidate_grams'],
 'candidate_error_g':stats['verify5']['candidate_grams']-5,'tolerance_g':.1,
 'verify5_minus_verify0_grams':verify_delta,'point_evidence':stats,
 'post_failure_unloaded_candidate_g':new_zero,'zero_shift_from_first_verify_g':shift_from_first_zero,
 'post_reboot_difference_verify5_minus_unloaded_g':new_boot_relative_load,
 'difference_vs_nominal_5g_g':new_boot_relative_load-5,
 'unloaded_zero_passed':abs(new_zero)<=.1,
 'same_boot_verify0_verify5':stats['verify0']['host_boot_id']==stats['verify5']['host_boot_id'],
 'verify5_and_post_failure_zero_same_host_boot':stats['verify5']['host_boot_id']==stats['verify0_after_failed5']['host_boot_id'],
 'current_jetson_time_valid':state['time']['time_valid'],'ai_health':state['ai']['health'],
 'worker_status':worker['status'],'safety':state['safety'],'ultrasonic_all_disabled':True,
 'grams':None,'actual_dispensed_grams':None,'actuator_commands_sent':False,'capture_performed':False,
 'next_action':'With tray still empty, visually inspect whether a wire/object touches the tray or load-cell mount and report; do not retare/refit or activate the candidate.'}
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=S/('verify5_failure_audit_'+stamp+'.json')
out.write_text(json.dumps(report,indent=2));(out.with_suffix('.json.sha256')).write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'\n')
print(json.dumps(report,indent=2))
