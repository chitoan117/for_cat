from pathlib import Path
from contextlib import closing
from datetime import datetime,timezone
import json,sqlite3,time

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
dbpath='/home/toan/for_cat/jetson/data/events.db'
update=json.loads((r/'schedule_1235_update.json').read_text())
plan=update['after']['plan_id']
due=int(datetime.fromisoformat(update['requested_due_at']).timestamp()*1000)
report={'plan_id':plan,'due_unix_ms':due,'trace':[]}
deadline=time.monotonic()+260;last=None;done_at=None
try:
    while time.monotonic()<deadline:
        with closing(sqlite3.connect(dbpath,timeout=2)) as db:
            raw=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
            ai=db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()
            occurrence=db.execute('SELECT o.request_id,r.decision FROM scheduled_occurrences o JOIN feed_dry_run_requests r USING(request_id) WHERE o.plan_id=? AND o.due_unix_ms=?',(plan,due)).fetchone()
        decision=json.loads(occurrence[1]) if occurrence and occurrence[1] else {}
        fc=raw['telemetry']['fc_live']
        row={'at':datetime.now(timezone.utc).isoformat(),'fc_live':fc,'decision':decision,
             'time_valid':raw.get('time_valid'),'ai':json.loads(ai[0]) if ai else None}
        report['trace'].append(row)
        state=(fc.get('bench_state'),decision.get('delivery_state'),fc.get('ai_oled'))
        if state!=last or len(report['trace'])%15==0:
            print(json.dumps({'at':row['at'],'bench':state[0],'delivery':state[1],
                              'oled':state[2],'grams':fc.get('signed_g'),
                              'dispensed_g':fc.get('dispensed_g')}),flush=True)
            last=state;(r/'schedule_1235_result.json').write_text(json.dumps(report,indent=2))
        if decision.get('delivery_state') in ('WEIGHT_REACHED','FAILED','REJECTED','EXPIRED','UNCERTAIN'):
            if done_at is None:done_at=time.monotonic();report['decision']=decision
            if time.monotonic()-done_at>8:
                with closing(sqlite3.connect(dbpath)) as db:
                    report['events']=db.execute('SELECT kind,occurred_at,body FROM esp32_events WHERE body LIKE ? ORDER BY seq',('%'+occurrence[0]+'%',)).fetchall()
                break
        time.sleep(1)
    if done_at is None:report['error']='NO_TERMINAL_RESULT_IN_MONITOR_WINDOW'
finally:
    (r/'schedule_1235_result.json').write_text(json.dumps(report,indent=2))
    print('RESULT '+json.dumps({k:v for k,v in report.items() if k!='trace'}),flush=True)
