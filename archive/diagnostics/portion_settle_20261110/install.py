from contextlib import closing
from pathlib import Path
import json,sqlite3,time,subprocess,sys,os
r=Path('/home/toan/for_cat/evidence/portion_settle_20261110')
with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db')) as db:
    before=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0
assert abs(time.monotonic()*1000-before['updated_monotonic_ms'])<2500
fc=before['telemetry']['fc_live'];assert fc['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?') and not fc.get('dog_running')
(r/'preflight.json').write_text(json.dumps(before,indent=2))
# Explicit neutral STOP before update; never assert an unobserved CLOSED position.
t=Path('/tmp/fc_pump_install_'+str(os.getpid())+'.txt');t.write_text('0\n')
try:os.link(str(t),'/tmp/for_cat_cmd.txt')
finally:t.unlink()
time.sleep(3)
try:
    subprocess.run(['systemctl','--user','stop','for-cat-api.service'],check=True)
    subprocess.run([sys.executable,str(r/'deploy_firmware.py'),'backup'],check=True)
    # Bridge opening USB can reset ESP32: consume STOP before any AI commands.
    t=Path('/tmp/fc_meal_after_reset_'+str(os.getpid())+'.txt');t.write_text('0\n')
    try:os.link(str(t),'/tmp/for_cat_cmd.txt')
    finally:t.unlink()
    subprocess.run([sys.executable,str(r/'deploy_firmware.py'),'flash'],check=True)
finally:
    subprocess.run(['systemctl','--user','start','for-cat-api.service','for-cat-esp32-bridge.service'],check=True)
print('INSTALL COMPLETE: feed remains paused. No pump-test or servo movement command sent.',flush=True)
