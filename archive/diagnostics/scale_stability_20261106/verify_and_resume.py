from pathlib import Path
import json,time,urllib.request,os
r=Path('/home/toan/for_cat/evidence/scale_stability_20261106')
def status():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as res:return json.load(res)
rows=[]
for _ in range(30):
 d=status();assert d['esp32']['connected'] and not d['esp32']['stale']
 assert d.get('bench_state')=='READY','Manual cycle active during stationary check'
 rows.append({'at':d['esp32']['last_telemetry_at'],'g':d['weight']['grams'],'raw':d['weight']['raw_counts']})
 (r/'stationary_bowl.json').write_text(json.dumps(rows,indent=2))
 time.sleep(1)
v=[x['g'] for x in rows[-20:]]
assert len(set(x['at'] for x in rows))>20,'Telemetry not advancing'
assert max(v)-min(v)<0.8 and all(abs(g)<1.5 for g in v),'Bowl not stationary/zero; automatic remains exited'
cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_zero_ready_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('start\nmode\nservo_position\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+4
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
assert any('exited=0' in x and 'inspect_lock=0' in x for x in lines)
after=status()
result={'owner_confirmed_previous_lifting_or_touching':True,'no_additional_tare':True,'stationary_samples':rows,
 'stationary_min_g':min(v),'stationary_max_g':max(v),'automatic_restored':True,'ack':lines,
 'after_ai':after.get('ai'),'after_e1_cm':after.get('approach',{}).get('distance_cm'),'after_grams':after.get('grams'),
 'after_bench_state':after.get('bench_state'),'direct_motor_commands_sent':False}
(r/'verified_resume.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='stationary_samples'},indent=2))
