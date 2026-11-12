from pathlib import Path
import shutil
r=Path(__file__).parent
for name in ['scheduled_worker.py','fc_live_bridge.py']:
 shutil.copy2(r/'before'/name,r/name)
p=r/'scheduled_worker.py';s=p.read_text()
needle="            db.commit()\n\n    def submit"
assert needle in s
s=s.replace(needle,'''            # Upgrade daily identity to scheduled-slot identity, retaining old receipts.
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='scheduled_occurrences'").fetchone()[0]
            if 'UNIQUE(plan_id,local_date)' in schema.replace(' ', ''):
                db.execute('BEGIN IMMEDIATE')
                db.execute('ALTER TABLE scheduled_occurrences RENAME TO scheduled_occurrences_daily_v1')
                db.execute('CREATE TABLE scheduled_occurrences('
                           'occurrence_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,local_date TEXT NOT NULL,'
                           'due_unix_ms INTEGER NOT NULL,plan_revision INTEGER NOT NULL,request_id TEXT NOT NULL UNIQUE,'
                           'created_at TEXT NOT NULL,origin TEXT NOT NULL,UNIQUE(plan_id,due_unix_ms))')
                db.execute('INSERT INTO scheduled_occurrences SELECT * FROM scheduled_occurrences_daily_v1')
                db.execute('DROP TABLE scheduled_occurrences_daily_v1')
            db.commit()

    def submit''',1)
s=s.replace("occurrence_id = 'occurrence_' + hashlib.sha256((plan_id+':'+result['local_date']).encode()).hexdigest()[:48]", "occurrence_id = 'occurrence_' + hashlib.sha256((plan_id+':'+str(result['due_unix_ms'])).encode()).hexdigest()[:48]")
s=s.replace("WHERE occurrence_id=?', (occurrence_id,)","WHERE plan_id=? AND due_unix_ms=?', (plan_id,result['due_unix_ms'])")
s=s.replace('''            # One daily slot per plan. Revision/name/time edits cannot cause a
            # second submission on an already-served Vietnam calendar date.''','''            # A renamed/retried slot is the same meal. An explicitly retimed
            # plan is a new slot even if the earlier time already ran today.''')
p.write_text(s)
shutil.copy2('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino',r/'before/esp32.ino')
(r/'esp32').mkdir(exist_ok=True)
shutil.copy2(r/'before/esp32.ino',r/'esp32/esp32.ino')
print('Prepared slot-identity migration and firmware baseline.')
