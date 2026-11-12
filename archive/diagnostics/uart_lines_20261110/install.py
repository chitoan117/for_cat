from pathlib import Path
import hashlib,json,os,subprocess,time
R=Path(__file__).resolve().parent
live=Path('/home/toan/for_cat/jetson/tools/fc_live_bridge.py')
meta=json.loads((R/'integrity.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(live)==meta['before'],'Live bridge changed'
assert sha(R/'fc_live_bridge.py')==meta['after']
assert not (R/'live_before.py').exists(),'Installer already attempted'
(R/'live_before.py').write_bytes(live.read_bytes())
subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
try:
    inbox=Path('/tmp/for_cat_cmd.txt')
    assert not inbox.exists(),'Pending manual command; inspect before replacement'
    t=Path('/tmp/forcat_line_install_%d'%os.getpid());t.write_text('0\n')
    try:os.link(t,inbox)
    finally:t.unlink()
    live.write_bytes((R/'fc_live_bridge.py').read_bytes())
    subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
    time.sleep(2)
    subprocess.run(['systemctl','--user','is-active','--quiet','for-cat-esp32-bridge.service'],check=True)
except BaseException:
    live.write_bytes((R/'live_before.py').read_bytes())
    subprocess.run(['systemctl','--user','restart','for-cat-esp32-bridge.service'],check=True)
    raise
print(json.dumps({'bridge_sha256':sha(live),'status':'installed','uart':'/dev/ttyTHS1','zero_not_yet_sent':True}),flush=True)
