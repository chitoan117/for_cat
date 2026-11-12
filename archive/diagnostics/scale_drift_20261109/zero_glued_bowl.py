from pathlib import Path
from contextlib import closing
from collections import deque
import os,time,json,sqlite3
root=Path('/home/toan/for_cat/evidence/water_pulse_20261109')
def send(body):
 p=Path('/tmp/fc_glued_zero_'+str(os.getpid())+'.txt');p.write_text(body+'\n')
 try:os.link(str(p),'/tmp/for_cat_cmd.txt')
 finally:p.unlink()
def sample():
 with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db')) as db:r=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
 assert abs(time.monotonic()*1000-r['updated_monotonic_ms'])<2500,'Stale scale'
 f=r['telemetry']['fc_live']
 assert f['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?') and not f.get('dog_running'),'Not idle'
 assert isinstance(f.get('signed_g'),(int,float)) and abs(f['signed_g'])<1000,'No valid weight'
 return f
send('pump_auto off\npump_off\n0');time.sleep(2)
window=deque(maxlen=8);deadline=time.monotonic()+30
while time.monotonic()<deadline:
 window.append(sample())
 if len(window)==8 and max(f['signed_g'] for f in window)-min(f['signed_g'] for f in window)<1.0:break
 time.sleep(1)
else:raise AssertionError('No stable window; no retare sent')
before=list(window)
# Owner freshly confirmed EMPTY bowl, dry/cooled glue, attached only to weighing platform.
send('t')
print(json.dumps({'tare_sent':True,'before':[f['signed_g'] for f in before]}),flush=True)
time.sleep(4)
after=[]
for _ in range(20):after.append(sample());time.sleep(1)
assert all(f['grams_per_count']==before[0]['grams_per_count'] for f in after),'Factor changed'
v=[f['signed_g'] for f in after]
out=root/('glued_bowl_zero_'+str(int(time.time()))+'.json')
out.write_text(json.dumps({'owner_confirmed_empty_glued_bowl':True,'before':before,'after':after},indent=2))
print(json.dumps({'after':v,'min':min(v),'max':max(v),'tare_counts':after[-1]['tare_counts'],'factor':after[-1]['grams_per_count'],'stable_within_1g':all(abs(x)<1 for x in v),'evidence':str(out)}),flush=True)
