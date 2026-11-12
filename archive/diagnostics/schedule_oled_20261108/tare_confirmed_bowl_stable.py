from pathlib import Path
from contextlib import closing
from collections import deque
import json, os, sqlite3, time

dbpath = Path('/home/toan/for_cat/jetson/data/events.db')
evidence = Path('/home/toan/for_cat/evidence/schedule_oled_20261108')

def sample():
    with closing(sqlite3.connect(dbpath)) as db:
        raw = json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert abs(time.monotonic()*1000 - raw['updated_monotonic_ms']) < 2500, 'Stale telemetry'
    fc = raw['telemetry']['fc_live']
    assert fc['bench_state'] == 'READY', ('Not idle', fc['bench_state'])
    assert isinstance(fc.get('signed_g'), (int, float)), 'Missing weight'
    assert not fc.get('dog_running'), 'Dog action active'
    assert -10 <= fc['signed_g'] <= 10, ('Unexpected bowl load', fc['signed_g'])
    return fc

window = deque(maxlen=8)
observed = []
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    fc = sample()
    window.append(fc)
    observed.append(fc['signed_g'])
    if len(window) == 8 and max(x['signed_g'] for x in window) - min(x['signed_g'] for x in window) < 1.5:
        break
    time.sleep(1)
else:
    raise AssertionError(('No stable 8-second window; no tare sent', observed))

before = list(window)
cmd = Path('/tmp/for_cat_cmd.txt')
temp = Path('/tmp/forcat_tare_confirmed_empty_' + str(os.getpid()) + '.txt')
with temp.open('x') as f:
    f.write('t\n')
try:
    os.link(str(temp), str(cmd))
finally:
    temp.unlink()
print(json.dumps({'tare_sent': True, 'stable_before': [x['signed_g'] for x in before]}), flush=True)
time.sleep(4)
after = []
for _ in range(15):
    after.append(sample())
    time.sleep(1)
assert all(x['grams_per_count'] == before[0]['grams_per_count'] for x in after), 'Calibration factor changed'
report = {'owner_confirmed_empty_bowl': True, 'observed_before': observed, 'before': before, 'after': after}
out = evidence / ('bowl_zero_' + str(int(time.time())) + '.json')
out.write_text(json.dumps(report, indent=2))
print(json.dumps({'after': [x['signed_g'] for x in after], 'tare_counts': after[-1]['tare_counts'],
                  'grams_per_count': after[-1]['grams_per_count'], 'evidence': str(out)}), flush=True)
assert all(abs(x['signed_g']) < 1 for x in after), 'Post-tare zero not stable'
