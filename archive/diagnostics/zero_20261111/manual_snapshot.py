from pathlib import Path
import json,sqlite3,time,subprocess
ROOT=Path('/home/toan/for_cat/jetson')
with sqlite3.connect(ROOT/'data/events.db',timeout=2) as db:
    state=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    requests=db.execute('SELECT request_id,body,decision FROM feed_dry_run_requests ORDER BY rowid DESC LIMIT 3').fetchall()
fc=state['telemetry']['fc_live']
print(json.dumps({'host_boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'telemetry_host_boot':state.get('host_boot_id'),'age_seconds':(time.monotonic()*1000-state['updated_monotonic_ms'])/1000,'device':state.get('device'),'device_ms':state['telemetry']['monotonic_ms'],'fc':{k:fc.get(k) for k in ('bench_state','demo_exited','inspect_required','device_feed_block_reason','meal_phase','signed_g','grams','tare_counts','grams_per_count','backup_enabled','backup_offline')},'button':state['telemetry']['sensors']['button'],'weight':state['telemetry']['sensors']['hx711'],'counters':state['counters'],'recent_feed_requests':requests},indent=2))
