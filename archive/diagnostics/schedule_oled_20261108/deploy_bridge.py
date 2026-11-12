from pathlib import Path
from contextlib import closing
import hashlib,json,sqlite3,subprocess,time

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
root=Path('/home/toan/for_cat/jetson')
target=root/'tools/fc_live_bridge.py'
expected='edd211f68634c85f30ca86cecfadfa73f0ba53523082e326913a49aebb9b7604'
candidate=(r/'fc_live_bridge.py').read_bytes()
compile(candidate,str(target),'exec')
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,'Live bridge changed; re-audit required'
assert not (r/'fc_live_bridge.py.before').exists(),'Backup exists; inspect before retry'
(r/'fc_live_bridge.py.before').write_bytes(target.read_bytes())
with closing(sqlite3.connect(root/'data/events.db')) as src, closing(sqlite3.connect(r/'events.before.db')) as dest:
    src.backup(dest)
service='for-cat-esp32-bridge.service'
subprocess.run(['systemctl','--user','stop',service],check=True)
try:
    assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
    temp=target.with_suffix('.py.clock_new')
    temp.write_bytes(candidate);temp.chmod(target.stat().st_mode);temp.replace(target)
    subprocess.run(['systemctl','--user','start',service],check=True)
except Exception:
    target.write_bytes((r/'fc_live_bridge.py.before').read_bytes())
    subprocess.run(['systemctl','--user','start',service])
    raise
for _ in range(20):
    time.sleep(.5)
    with closing(sqlite3.connect(root/'data/events.db')) as db:
        latest=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    if abs(time.monotonic()*1000-latest.get('updated_monotonic_ms',0))<2000 and latest.get('time_valid') is True:
        break
else:
    raise RuntimeError('New bridge must report fresh, clock-confirmed telemetry')
subprocess.run(['systemctl','--user','is-active',service],check=True)
result={'installed_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'time_valid':latest.get('time_valid'),'boot_id':latest.get('host_boot_id'),
        'fc_live':latest.get('telemetry',{}).get('fc_live'),
        'clock':json.loads((root/'data/clock_trust_v1.json').read_text()),
        'no_feed_commands_sent_by_installer':True}
(r/'deployment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
