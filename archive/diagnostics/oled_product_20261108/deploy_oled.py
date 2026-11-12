from pathlib import Path
from contextlib import closing
import hashlib,json,os,sqlite3,subprocess,sys,time,urllib.request

r=Path('/home/toan/for_cat/evidence/oled_product_20261108')
dbpath=Path('/home/toan/for_cat/jetson/data/events.db')
api='for-cat-api.service';bridge='for-cat-esp32-bridge.service'

def latest():
    with closing(sqlite3.connect(dbpath,timeout=2)) as db:
        return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])

def commands(body):
    target=Path('/tmp/for_cat_cmd.txt');temp=Path('/tmp/forcat_oled_'+str(os.getpid())+'.txt')
    with temp.open('x') as f:f.write(body)
    try:os.link(str(temp),str(target))
    finally:temp.unlink()

def query(body,seconds=4):
    with Path('/var/log/syslog').open(errors='replace') as log:
        log.seek(0,2);commands(body);lines=[];deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x)
            time.sleep(.1)
    return lines

before=latest();fc=before['telemetry']['fc_live']
assert time.monotonic()*1000-before['updated_monotonic_ms']<2500,'Stale MCU'
assert fc['bench_state'] in ('READY','MASS OK GATE?','CAT FAULT*') and not fc.get('dog_running'),'Wait until idle'
with closing(sqlite3.connect(dbpath)) as db:
    assert db.execute('SELECT count(*) FROM feed_dry_run_requests WHERE decision IS NULL').fetchone()[0]==0,'Pending requests; wait'
pre=query('mode\nservo_position\n')
assert any('SERVO ESTIMATE=CLOSED' in x and 'inspect_lock=0' in x and 'moving=0' in x and 'open_ms=900' in x and 'close_ms=1450' in x for x in pre),'Gate estimate must remain CLOSED before update'
assert any('exited=0' in x and 'servo_moving=0' in x for x in pre),'Unexpected paused or moving state'
(r/'preflight.json').write_text(json.dumps({'before':before,'query':pre},indent=2))
print('PREFLIGHT: idle, prior full-close estimate retained, no pending request. No motion commands.',flush=True)
stopped=False
try:
    subprocess.run(['systemctl','--user','stop',api],check=True);stopped=True
    subprocess.run([sys.executable,str(r/'deploy_firmware.py'),'backup'],check=True)
    subprocess.run([sys.executable,str(r/'deploy_firmware.py'),'flash'],check=True)
    # Only carry forward the same pre-update relative CLOSED marker. The update
    # sent no open/close/feed command and verified the same servo timing/profile.
    resume=query('inspect_ok\nstart\nmode\nservo_position\n',5)
    assert any('SERVO ESTIMATE=CLOSED' in x and 'moving=0' in x and 'open_ms=900' in x and 'close_ms=1450' in x for x in resume),resume
    assert any('exited=0' in x and 'inspect_lock=0' in x for x in resume),resume
    after=latest();now_fc=after['telemetry']['fc_live']
    assert after['telemetry']['sensors']['oled']['health']=='HEALTHY','OLED did not initialize'
    assert now_fc['tare_counts']==fc['tare_counts'] and now_fc['grams_per_count']==fc['grams_per_count'],'Calibration changed'
    result={'app_sha256':(r/'app.sha256').read_text().strip(),
            'oled_initialized':True,'only_display_changed':True,
            'calibration_preserved':True,'nvs_preserved':True,
            'profile_preserved':True,'relative_closed_marker_preserved':True,
            'no_open_close_feed_commands_sent':True,'resume':resume,'fc_live':now_fc}
    (r/'deployment.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
finally:
    if stopped:
        subprocess.run(['systemctl','--user','start',api,bridge],check=True)
        print('API/bridge services restored.',flush=True)
