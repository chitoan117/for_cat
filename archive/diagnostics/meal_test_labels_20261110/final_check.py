from pathlib import Path
import json,subprocess,urllib.request,hashlib
r=Path(__file__).parent
with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=3) as f:data=json.load(f)
ids={'meal_665a209ccdc767d1','meal_947ad5ff28780bb3'}
records=[x for x in data['records'] if x.get('meal_id') in ids]
assert len(records)==2 and all(x['observation_mode']=='MANUAL_TEST' and x['behavior_validated'] is False for x in records)
assert {x['food']:x['classification'] for x in records}=={'FOOD_A':'LIKE','FOOD_B':'DISLIKE'}
live=data['live'];assert live['selected_food']=='FOOD_B' and live['demo_exited'] is False
assert abs(live['tare_counts']+700653.3333333334)<.001 and abs(live['grams_per_count']+.000945082600219258)<1e-12
units={u:subprocess.check_output(['systemctl','--user','show',u,'-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True).strip() for u in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service')}
assert all('ActiveState=active' in x for x in units.values())
result={'records':records,'live':live,'services':units,'main_sha256':hashlib.sha256(Path('/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2/main.dart.js').read_bytes()).hexdigest(),'ui_verified_manual_test_labels':True}
(r/'final_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'records':[{k:x[k] for k in ('food','starting_g','remaining_g','consumed_g','classification','observation_mode')} for x in records],
 'auto_enabled':not live['demo_exited'],'selected_food':live['selected_food'],'services':units,'main_sha256':result['main_sha256']},indent=2),flush=True)
