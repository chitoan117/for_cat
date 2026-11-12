"""Full existing backend regression suite plus reused portable dispense policy."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/overnight_integration_20261023'/('regressions_'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S'))
OUT.mkdir()
records=[]
for name,command in [
    ('backend_all',[sys.executable,'-m','pytest','jetson/tests','-q','-ra']),
    ('dispense_policy_ubsan',['sh',str(ROOT/'scripts/verify_dispense_preparation.sh')]),
    ('pip_check',[sys.executable,'-m','pip','check']),
    ('git_diff_check',['git','diff','--check'])]:
    result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'jetson')+':'+str(ROOT)},
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
    (OUT/(name+'.log')).write_bytes(result.stdout)
    records.append({'name':name,'command':command,'exit_code':result.returncode})
    (OUT/'commands.json').write_text(json.dumps(records,indent=2))
    print(result.stdout.decode('utf-8','replace'),flush=True)
    if result.returncode:raise SystemExit(name+' FAILED: '+str(OUT))
print('REGRESSIONS_PASS',OUT)
