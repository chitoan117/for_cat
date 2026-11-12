from contextlib import closing
from pathlib import Path
import json, sqlite3, time

dbpath = '/home/toan/for_cat/jetson/data/events.db'
samples = []
last = None
for _ in range(45):
    with closing(sqlite3.connect(dbpath)) as db:
        esp = json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        ai = json.loads(db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()[0])
    fc = esp['telemetry']['fc_live']
    e1 = esp['telemetry']['sensors']['approach']
    row = {'time':esp['last_received_at'], 'state':fc['bench_state'], 'g':fc['signed_g'],
           'E1':e1['distance_cm'], 'ai':ai['classification'], 'confidence':ai['confidence'],
           'cat_triggers':esp['counters']['cat_triggers'], 'dog_triggers':esp['counters']['dog_triggers']}
    samples.append(row)
    key = (row['state'], row['ai'], row['cat_triggers'], row['dog_triggers'])
    if key != last:
        print(json.dumps(row), flush=True)
        last = key
    time.sleep(1)
out = Path('/home/toan/for_cat/evidence/schedule_oled_20261108')/('cat_retry_'+str(int(time.time()))+'.json')
out.write_text(json.dumps(samples, indent=2))
print(json.dumps({'evidence':str(out), 'last':samples[-1]}), flush=True)
