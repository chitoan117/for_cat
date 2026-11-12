"""Compile/test only the NEW existing-fd callback adapter; never opens a real fd."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent;out=ROOT/'bridge_link_tests';out.mkdir()
commands=[]


def run(args,label):
    q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (out/(label+'.log')).write_bytes(q.stdout)
    commands.append(dict(command=[str(x) for x in args],timestamp_utc=datetime.now(timezone.utc).isoformat(),exit_code=q.returncode,log=label+'.log'))
    if q.returncode:raise RuntimeError(label+' failed')
    return q.stdout.decode()


run([ROOT.parents[1]/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-Wall','-Wextra','-Werror',
     '-I'+str(ROOT/'firmware/include'),'-I'+str(ROOT/'bridge'),ROOT/'tests/bridge_link_test.cpp','-o',out/'bridge_link.exe'],'compile')
text=run([out/'bridge_link.exe'],'test')
result=dict(status='PASS_OFFLINE',new_callback_assertions=int(re.search(r'checks=(\d+)',text).group(1)),
    source='MOCK_WRITER_STORE_CALLBACKS',physical_pass=False,real_fd_opened=False,commands=commands)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
