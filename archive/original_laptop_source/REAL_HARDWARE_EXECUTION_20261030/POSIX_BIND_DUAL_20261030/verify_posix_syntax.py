"""Object-compile real Linux/POSIX branch on Windows; no linking/ARM64/device run."""
from datetime import datetime,timezone
import ast
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--label');a=p.parse_args()
if a.label and not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('posix_syntax_'+a.label if a.label else 'posix_syntax');out.mkdir()
lib=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install'
args=[WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-target','x86_64-linux-gnu','-std=c++14','-Wall','-Wextra','-Werror',
    '-c','-DFORCAT_POSIX_SYNTAX_CHECK=1','-I'+str(ROOT/'compat'),'-I'+str(ROOT/'bridge'),
    '-I'+str(ROOT/'firmware/include'),'-I'+str(lib/'include'),ROOT/'bridge/esp32_bridge.cpp','-o',out/'bridge_posix.o']
start=datetime.now(timezone.utc).isoformat()
q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
(out/'compile.log').write_bytes(q.stdout)
result=dict(status='PASS_OFFLINE' if q.returncode==0 else 'FAIL',kind='LINUX_X86_64_POSIX_BRANCH_OBJECT_ONLY',command=[str(x) for x in args],
    timestamp_utc=start,exit_code=q.returncode,target_link='NOT_RUN',Jetson_ARM64='NOT_RUN',real_serial='NOT_RUN')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if q.returncode:raise SystemExit(q.returncode)
ast.parse((ROOT/'manual_console_dual.py').read_text(),feature_version=(3,6))
p=subprocess.run([sys.executable,'-B',str(ROOT/'manual_console_dual.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
(out/'console_plan.log').write_bytes(p.stdout)
assert p.returncode==0 and json.loads(p.stdout)['mode']=='PLAN_ONLY'
print(json.dumps(result,indent=2))
