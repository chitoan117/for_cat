from pathlib import Path
from contextlib import closing
import json, os, re, sqlite3, time

root = Path('/home/toan/for_cat')
dbpath = root/'jetson/data/events.db'

def live():
    with closing(sqlite3.connect(dbpath)) as db:
        raw = json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert abs(time.monotonic()*1000 - raw['updated_monotonic_ms']) < 2500, 'Stale status'
    fc = raw['telemetry']['fc_live']
    assert fc['bench_state'] in ('READY', 'CAT FAULT*'), fc['bench_state']
    assert not fc.get('dog_running'), 'Dog alarm active'
    assert isinstance(fc.get('signed_g'), (float,int)) and abs(fc['signed_g']) <= 2, 'Bowl not near zero'
    return fc

def send(cmd):
    target = Path('/tmp/for_cat_cmd.txt')
    temp = Path('/tmp/fc_idle_recovery_' + str(os.getpid()) + '.txt')
    with temp.open('x') as f:
        f.write(cmd+'\n')
    try:
        os.link(str(temp), str(target))
    finally:
        temp.unlink()

before = live()
with open('/var/log/syslog', 'rb') as f:
    f.seek(0,2)
    offset = f.tell()
send('servo_position')
time.sleep(3)
with open('/var/log/syslog', 'rb') as f:
    f.seek(offset)
    text = f.read().decode('utf-8','replace')
matches = re.findall(r'SERVO ESTIMATE=([^\r\n]+)', text)
assert matches, 'No fresh servo diagnostic response'
gate = matches[-1]
assert gate.startswith('CLOSED ') and 'inspect_lock=0 moving=0 ' in gate, gate
current = live()
if current['bench_state'] == 'CAT FAULT*':
    # stop sends neutral and clears idle dose-fault, preserving any inspection lock.
    # It does not assert a physical CLOSED position or issue opening/closing motion.
    send('stop')
    time.sleep(3)
after = live()
assert after['bench_state'] == 'READY', after['bench_state']
result = {'before':before, 'gate_diagnostic':gate, 'after':after,
          'recovery':'neutral_stop_only_no_motion_no_tare_no_inspection_override'}
out = root/'evidence/schedule_oled_20261108'/('idle_recovery_'+str(int(time.time()))+'.json')
out.write_text(json.dumps(result, indent=2))
print(json.dumps({'before':before['bench_state'], 'gate':gate, 'after':after, 'evidence':str(out)}))
