"""Back up canonical SQLite and stage two tested read-only user services."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

if sys.version_info < (3, 7):
    raise RuntimeError('Use .venv/jetson-integration/bin/python for SQLite online backup')

ROOT=Path('/home/toan/for_cat')
E=ROOT/'evidence/overnight_integration_20261023'
backup=E/'canonical_database.before.sqlite'
if backup.exists() and backup.stat().st_size==0:
    backup.rename(E/'canonical_database.empty_from_py36.sqlite')
with sqlite3.connect(str(ROOT/'jetson/data/events.db')) as source:
    counts={table:source.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
            for table in ('events','feed_requests','typed_records')}
    assert counts['events']<=100000
    if not backup.exists():
        with sqlite3.connect(str(backup)) as dest:source.backup(dest)
(E/'database_before.json').write_text(json.dumps(counts,indent=2))
# Provide empty staging parents for exact reusable policy/config transfers.
for path in ['/tmp/for_cat_overnight_stage/esp32/include/m4','/tmp/for_cat_overnight_stage/esp32/test',
             '/tmp/for_cat_overnight_stage/config']:
    Path(path).mkdir(parents=True,exist_ok=True)
units=Path.home()/'.config/systemd/user'
units.mkdir(parents=True,exist_ok=True)
for name in ('for-cat-esp32-bridge.service','for-cat-api.service','for-cat-ai.service'):
    src=ROOT/'deploy/systemd'/name;dst=units/name
    if dst.exists() and dst.read_bytes()!=src.read_bytes():
        previous_api=src.read_text().replace('Environment=SYSTEM_STATE_PROVIDER=REAL\n','').replace('Environment=API_HOST=0.0.0.0','Environment=API_HOST=127.0.0.1')
        previous_ai=src.read_text().replace('/bin/bash -o pipefail -c','/bin/sh -c').replace('StandardError=journal\n','')
        previous_ai_pipeline=src.read_text().replace('ExecStart=/bin/bash %h/for_cat/scripts/run_existing_ai.sh',
            "ExecStart=/bin/bash -o pipefail -c '/usr/bin/stdbuf -oL %h/for_cat/jetson/ai/cat_dog_trt --headless --no-snapshot | %h/for_cat/.native-build/esp32/ai_state_tap %h/for_cat/jetson/data/events.db'")
        assert (name=='for-cat-api.service' and dst.read_text()==previous_api) or (name=='for-cat-ai.service' and dst.read_text() in (previous_ai,previous_ai_pipeline)),str(dst)
        shutil.copy2(dst,E/(name+'.before_'+hashlib.sha256(dst.read_bytes()).hexdigest()[:12]))
    shutil.copy2(src,dst)
verification=subprocess.run(['systemd-analyze','--user','verify',str(units/'for-cat-esp32-bridge.service'),str(units/'for-cat-api.service')],
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(E/'systemd_analyze_verify.log').write_bytes(verification.stdout)
if verification.returncode:
    print('systemd-analyze --user verify unavailable in this SSH/cgroup context:',verification.stdout.decode())
subprocess.check_call(['systemctl','--user','daemon-reload'])
loaded=subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge.service','for-cat-api.service','for-cat-ai.service','-p','LoadState','-p','FragmentPath','-p','ExecStart'])
assert loaded.count(b'LoadState=loaded')==3,loaded
(E/'systemd_loaded_units.txt').write_bytes(loaded)
print('DATABASE BACKUP',counts,'USER UNITS LOAD PASS; NOT ENABLED; START/ACTIVE CHECK IS SEPARATE')
