from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib, json, sqlite3, subprocess, time, urllib.request

root = Path('/home/toan/for_cat/jetson')
report = {'captured_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat()}
with closing(sqlite3.connect(root/'data/events.db')) as db:
    for table in ('esp32_latest', 'ai_latest'):
        report[table] = json.loads(db.execute('SELECT body FROM '+table+' WHERE id=1').fetchone()[0])
    report['pending_requests'] = db.execute('SELECT request_id,body,decision FROM feed_dry_run_requests WHERE decision IS NULL').fetchall()
for route in ('/api/meal-plans', '/api/meal-plans/worker'):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000'+route, timeout=5) as response:
            report[route] = json.load(response)
    except Exception as exc:
        report[route] = {'error':str(exc)}
report['services'] = {}
for svc in ('for-cat-api.service', 'for-cat-esp32-bridge.service', 'for-cat-ai.service'):
    report['services'][svc] = subprocess.check_output(['systemctl','--user','show',svc,'-p','ActiveState','-p','UnitFileState','-p','NRestarts'], text=True).strip()
report['hashes'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'tools/fc_live_bridge.py', root/'app/scheduled_worker.py')}
report['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
report['uptime_seconds'] = float(Path('/proc/uptime').read_text().split()[0])
report['telemetry_age_ms'] = time.monotonic()*1000 - report['esp32_latest']['updated_monotonic_ms']
with open('/var/log/syslog','rb') as f:
    f.seek(0,2)
    f.seek(max(0,f.tell()-100000))
    lines = f.read().decode('utf-8','replace').splitlines()
report['recent_motor_log'] = [s for s in lines if '[esp32]' in s or 'AI_CAT_DETECTED' in s][-25:]
report['recent_oc_log'] = [s for s in lines if 'OC ALARM' in s][-3:]
print(json.dumps(report, ensure_ascii=False, indent=2))
