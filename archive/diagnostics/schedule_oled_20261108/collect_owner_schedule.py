from pathlib import Path
from contextlib import closing
import json,sqlite3,subprocess

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
identifier='schedule_f38471d3fda509a0d3afddfaf28c84b5c0ff60e4915ed1b1'
with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db')) as db:
    report={
        'request':db.execute('SELECT request_id,body,decision FROM feed_dry_run_requests WHERE request_id=?',(identifier,)).fetchone(),
        'delivery':db.execute('SELECT * FROM scheduled_delivery WHERE request_id=?',(identifier,)).fetchone(),
        'occurrence':db.execute('SELECT * FROM scheduled_occurrences WHERE request_id=?',(identifier,)).fetchone(),
        'events':db.execute('SELECT kind,occurred_at,body FROM esp32_events WHERE body LIKE ? ORDER BY seq',('%'+identifier+'%',)).fetchall(),
        'esp32_latest':json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0]),
    }
report['serial_log']=subprocess.check_output(['bash','-c',"grep -aE 'feed_once|MANUAL FEED \\(SCHEDULED\\)|CAT WEIGHT TIMEOUT|CAT CLOSING NOW|CAT SERVO STOPPED' /var/log/syslog | tail -n 26"],text=True)
(r/'owner_schedule_1225.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ('request','delivery','occurrence','events')},indent=2))
