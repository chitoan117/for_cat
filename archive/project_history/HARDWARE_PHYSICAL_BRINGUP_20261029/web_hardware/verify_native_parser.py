"""Actual Windows C++14/json-c tests of candidate, never target/serial execution."""
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];KIT=HERE.parent
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def run(args,name):
    p=subprocess.run([str(x) for x in args],cwd=HERE,capture_output=True,timeout=240,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
    (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(name+' failed; see log')
    print(name+': PASS',flush=True);return (p.stdout+p.stderr).decode('utf-8','replace')
def main():
    out=HERE/'native_parser';out.mkdir(exist_ok=True)
    include=HERE/'native_jsonc_install/include';library=HERE/'native_jsonc_install/lib/libjson-c.a'
    if not library.is_file():raise ValueError('build pinned local json-c dependency first')
    common=[ZIG,'c++','-std=c++14','-O1','-Wall','-Wextra','-Werror','-I'+str(HERE/'bridge_candidate'),'-I'+str(include)]
    run(common+[HERE/'bridge_candidate/parser_replay.cpp',library,'-ladvapi32','-o',out/'parser_replay.exe'],'parser_replay_compile')
    run(common+[HERE/'bridge_candidate/test_session.cpp','-o',out/'test_session.exe'],'session_compile')
    session=run([out/'test_session.exe'],'session_tests')
    text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',HERE/'native_parser_tests.py'],'native_parser_tests')
    result={'completed_at':datetime.now().astimezone().isoformat(),'OFFLINE_CPP14_JSONC_TEST_PASS':True,
        'parser_test_groups':int(re.search(r'(\d+) passed',text).group(1)),'session_stdout':session.strip(),
        'host':'WINDOWS','kit_revision':'GCC75_R1','ARM64_NATIVE_TEST_PASS':False,
        'ARM64_R1_RETEST':'NOT_RUN','latest_owner_ARM64_attempt':'FAIL_GCC75_MISLEADING_INDENTATION',
        'whole_posix_bridge_binary_built_on_windows':False,
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'bridge_candidate').iterdir()) if p.suffix in ('.h','.cpp')},
        'serial_opened':False,'actuator_tx':False,'physical_pass':False,'dependency':json.loads((HERE/'jsonc_dependency.json').read_text())}
    (HERE/'native_parser_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
