from pathlib import Path
from contextlib import closing
from datetime import datetime,timezone
import json,sqlite3,time

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
rows=[];previous=None
for _ in range(60):
    with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db',timeout=1)) as db:
        ai=json.loads(db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()[0])
        raw=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    fc=raw['telemetry']['fc_live']
    row={'at':datetime.now(timezone.utc).isoformat(),'ai':ai,'fc_live':fc}
    rows.append(row)
    state=(ai.get('classification'),fc.get('ai_oled'),fc.get('bench_state'))
    if state!=previous or len(rows)%10==0:
        print(json.dumps({'at':row['at'],'ai':state[0],'confidence':ai.get('confidence'),
                          'oled':state[1],'bench':state[2],'grams':fc.get('signed_g')}),flush=True)
        previous=state
    time.sleep(1)
(r/'ai_oled_live.json').write_text(json.dumps(rows,indent=2))
