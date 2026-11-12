"""NEW optional UI harness only, consumes actual sandbox API response fixtures."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--backend-output',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('flutter_'+a.label);out.mkdir()
fixtures=(a.backend_output/'ui_fixtures').resolve()
result={'status':'FAIL','physical_pass':False,'production_accessed':False,'commands':[]}


def run(args,label):
    command=['D:/dev/flutter/bin/flutter.bat']+args
    q=subprocess.run(command,cwd=ROOT/'flutter',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,
       env={**os.environ,'FORCAT_UI_FIXTURES':str(fixtures),'FLUTTER_SUPPRESS_ANALYTICS':'true','PYTHONIOENCODING':'utf-8'})
    (out/(label+'.log')).write_bytes(q.stdout);result['commands'].append({'command':command,'exit_code':q.returncode,'log':label+'.log','timestamp_utc':datetime.now(timezone.utc).isoformat()})
    if q.returncode:raise RuntimeError(label+' failed; preserve output')
    return q.stdout.decode('utf-8','replace')


try:
    run(['pub','get','--offline'],'pub')
    text=run(['test','--no-pub','--reporter','expanded','test/closed_loop_test.dart'],'tests')
    run(['analyze','--no-pub'],'analyze')
    run(['build','web','--no-pub','--base-href','/flutter/'],'build_web')
    result.update(status='PASS_OFFLINE',new_flutter_tests=int(re.search(r'\+(\d+): All tests passed',text).group(1)),
                  analyze='NO_ISSUES',build_web='PASS',fixture_source='CONNECTED_MOCK_PROTOCOL_CONTROLLER_SQL_ASGI_RESPONSES')
except Exception as e:result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
