"""Build entire actual Bridge source with OS-only no-tty IO replacement on Windows."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--compile-only',action='store_true');a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('bind_tests_'+a.label);out.mkdir()
result=dict(status='FAIL',physical_pass=False,source='ACTUAL_BRIDGE_SOURCE_MOCK_OS_AND_MCU_IO',commands=[])


def run(args,name):
    row=dict(command=[str(x) for x in args],timestamp_utc=datetime.now(timezone.utc).isoformat())
    q=subprocess.run(row['command'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,
        env={**os.environ,'PYTHONPATH':str(ROOT),'FORCAT_BOUND_OUT':str(out),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
    (out/(name+'.log')).write_bytes(q.stdout);row.update(exit_code=q.returncode,log=name+'.log');result['commands'].append(row)
    if q.returncode:raise RuntimeError(name+' failed; preserve output')
    return q.stdout.decode('utf-8','replace')


try:
    lib=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029/web_hardware/native_jsonc_install'
    run([WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','dlltool','-m','i386:x86-64',
         '-d',ROOT/'compat/winsqlite3.def','-l',out/'libwinsqlite3.a'],'sqlite_import_library')
    run([WS/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Werror',
        '-DFORCAT_BRIDGE_TEST=1','-D_CRT_SECURE_NO_WARNINGS=1','-I'+str(ROOT/'compat'),'-I'+str(ROOT/'bridge'),
        '-I'+str(ROOT/'tests'),'-I'+str(ROOT/'firmware/include'),'-I'+str(lib/'include'),ROOT/'tests/production_source_main.cpp',
        lib/'lib/libjson-c.a','-ladvapi32',out/'libwinsqlite3.a','-o',out/'actual_bridge_test.exe'],'compile_actual_source')
    if not a.compile_only:
        text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',ROOT/'tests/test_bound_bridge.py'],'integration')
        result['new_integration_cases']=int(re.search(r'(\d+) passed',text).group(1))
    result.update(status='PASS_OFFLINE',linux_syscalls='NOT_RUN_WINDOWS_OS_REPLACEMENT',old_suites_rerun=False)
except Exception as e:result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
