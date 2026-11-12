from pathlib import Path
from contextlib import closing
import json,os,sqlite3,time

dbpath=Path('/home/toan/for_cat/jetson/data/events.db')
r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
def sample():
    with closing(sqlite3.connect(dbpath)) as db:
        raw=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert abs(time.monotonic()*1000-raw['updated_monotonic_ms'])<2500
    fc=raw['telemetry']['fc_live'];assert fc['bench_state'] in ('READY','MASS OK GATE?','CAT FAULT*'),fc
    assert isinstance(fc.get('signed_g'),(int,float)),fc
    return fc
before=[sample()]
for _ in range(7):time.sleep(1);before.append(sample())
values=[x['signed_g'] for x in before]
assert max(values)-min(values)<1.5,('Scale not stable',values)
# Current valid bowl offset must be close to zero. A removed bowl (~-25g)
# or a previous serving (~35g) must not be accepted for this fresh confirmation.
assert all(-10<=g<=10 for g in values),('Unexpected load; reconfirm bowl',values)
cmd=Path('/tmp/for_cat_cmd.txt');temp=Path('/tmp/forcat_tare_confirmed_empty_'+str(os.getpid())+'.txt')
with temp.open('x') as f:f.write('t\n')
try:os.link(str(temp),str(cmd))
finally:temp.unlink()
time.sleep(4)
after=[]
for _ in range(15):after.append(sample());time.sleep(1)
assert all(x['grams_per_count']==before[0]['grams_per_count'] for x in after),'Calibration factor changed'
report={'owner_confirmed_empty_bowl':True,'before':before,'after':after}
(r/('bowl_zero_'+str(int(time.time()))+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({'before':values,'after':[x['signed_g'] for x in after],
                  'tare_counts':after[-1]['tare_counts'],'grams_per_count':after[-1]['grams_per_count']}))
assert all(abs(x['signed_g'])<1 for x in after),'Zero not stable'
