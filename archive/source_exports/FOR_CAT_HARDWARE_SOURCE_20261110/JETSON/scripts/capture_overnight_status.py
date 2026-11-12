"""Read-only live API/USB/Git evidence. Never sends a serial or feed command."""
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import urllib.request

ROOT=Path('/home/toan/for_cat')
E=ROOT/'evidence/overnight_integration_20261023'
result={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'api':{},'commands':{},'protected_hashes':{}}
for path in ['/api/v1/health','/api/v1/status','/api/v1/readiness','/api/v1/esp32/status','/api/v1/esp32/events']:
    with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as response:
        result['api'][path]=json.load(response)
for name,args in {
    'usb':['lsusb'],
    'serial_devices':['sh','-c','ls -l /dev/serial/by-id/ /dev/ttyACM* /dev/ttyUSB* 2>/dev/null'],
    'services':['systemctl','--user','show','for-cat-esp32-bridge.service','for-cat-api.service','-p','ActiveState','-p','SubState','-p','NRestarts','-p','UnitFileState'],
    'listeners':['ss','-ltnp'],
    'git_status':['git','status','--short'],
    'git_diffstat':['git','diff','--stat'],
    'diff_check':['git','diff','--check'],
}.items():
    p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
    result['commands'][name]={'exit_code':p.returncode,'output':p.stdout.decode('utf-8','replace')}
for path in ['jetson/ai/cat_dog_trt.cpp','jetson/ai/cat_dog_trt','models/tensorrt/yolov8n_320_fp16.engine']:
    result['protected_hashes'][path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
audit=json.loads((E/'audit.json').read_text())
result['ai_hashes_unchanged']=result['protected_hashes']==audit['protected_hashes']
result['git_index_unchanged']=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==audit['git_index_sha256']
with sqlite3.connect(str(ROOT/'jetson/data/events.db')) as db:
    result['database']={'user_version':db.execute('PRAGMA user_version').fetchone()[0],
                        'counts':{name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                                  for name in ['events','feed_requests','typed_records','esp32_events']},
                        'quick_check':db.execute('PRAGMA quick_check').fetchone()[0]}
assert result['ai_hashes_unchanged'] and result['git_index_unchanged']
assert result['api']['/api/v1/esp32/status']['actuator_execution'] is False
assert result['api']['/api/v1/esp32/status']['serial_tx_enabled'] is False
(E/'live_status.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
