from pathlib import Path
from contextlib import closing
import json,os,sqlite3,time,urllib.request

root=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
dbpath=Path('/home/toan/for_cat/jetson/data/events.db')
cmd=Path('/tmp/for_cat_cmd.txt')
tmp=Path('/tmp/forcat_readonly_status_'+str(os.getpid())+'.txt')
with tmp.open('x') as f:f.write('mode\nservo_position\nweight\n')
try:
    os.link(str(tmp),str(cmd))
finally:tmp.unlink()
rows=[]
for _ in range(20):
    with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=3) as response:
        s=json.load(response)
    with closing(sqlite3.connect(dbpath)) as db:
        raw=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    row={'at':s['observed_at'],'weight':s.get('weight'),
         'fc_live':raw.get('telemetry',{}).get('fc_live'),
         'ai':s.get('ai'),
         'distances':{k:v.get('distance_cm') for k,v in s['ultrasonic'].items()}}
    rows.append(row)
    print(json.dumps({k:row[k] for k in ('at','fc_live','distances')},separators=(',',':')),flush=True)
    time.sleep(1)
(root/'observation.json').write_text(json.dumps(rows,indent=2))
