from pathlib import Path
from contextlib import closing
import hashlib,json,sqlite3,subprocess

root=Path('/home/toan/for_cat/jetson')
with closing(sqlite3.connect(root/'data/events.db')) as db:
    for table in ('esp32_latest','ai_latest'):
        row=db.execute('SELECT body FROM '+table+' WHERE id=1').fetchone()
        print(table, row[0] if row else None)
    for table,sql in {
        'pending': 'SELECT request_id,body,decision FROM feed_dry_run_requests WHERE decision IS NULL',
        'deliveries': 'SELECT * FROM scheduled_delivery',
        'scheduled_events': "SELECT * FROM esp32_events WHERE kind IN ('scheduled_ack','scheduled_result') ORDER BY seq DESC LIMIT 12",
    }.items():
        print(table,json.dumps(db.execute(sql).fetchall()))
for svc in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service'):
    print(subprocess.check_output(['systemctl','--user','show',svc,'-p','ExecStart','-p','StandardOutput','-p','StandardError','-p','ActiveEnterTimestamp','-p','NRestarts'],text=True))
for p in (root/'tools/fc_live_bridge.py',root/'app/scheduled_worker.py'):
    print('sha256',str(p),hashlib.sha256(p.read_bytes()).hexdigest())
