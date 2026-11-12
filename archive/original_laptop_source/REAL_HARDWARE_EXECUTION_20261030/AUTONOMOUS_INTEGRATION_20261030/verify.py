"""NEW protocol/controller/SQLite/ASGI regressions only; no Serial/network/old suite."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW simple label')
out=ROOT/('tests_'+a.label);out.mkdir();(out/'ui_fixtures').mkdir()
result={'status':'FAIL','source':'OFFLINE_MOCK_COMPONENTS_CONNECTED','physical_pass':False,'commands':[]}


def run(args,label):
    entry={'command':[str(x) for x in args],'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    q=subprocess.run(entry['command'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,
        env={**os.environ,'PYTHONPATH':str(ROOT),'FORCAT_INTEGRATION_OUT':str(out),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
    (out/(label+'.log')).write_bytes(q.stdout);entry.update(exit_code=q.returncode,log=label+'.log');result['commands'].append(entry)
    if q.returncode:raise RuntimeError(label+' failed; output retained')
    return q.stdout.decode('utf-8','replace')


try:
    lib=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install'
    run([WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Werror',
         '-I'+str(ROOT/'firmware/include'),'-I'+str(lib/'include'),ROOT/'tests/device_worker.cpp',lib/'lib/libjson-c.a',
         '-ladvapi32','-o',out/'device_worker.exe'],'native_compile')
    text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',ROOT/'tests/test_integration.py',ROOT/'tests/test_edge_cases.py'],'integration')
    result.update(status='PASS_OFFLINE',new_pytest_cases=int(re.search(r'(\d+) passed',text).group(1)),
                  old_suites_rerun=False,serial_opened=False,camera_opened=False,production_accessed=False)
except Exception as e:
    result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
