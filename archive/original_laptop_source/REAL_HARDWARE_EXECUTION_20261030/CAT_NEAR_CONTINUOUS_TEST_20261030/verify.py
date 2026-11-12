"""Only new fork tests, including actual app loop with mocked hardware. No UART."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--cxx',default=str(ROOT.parents[1]/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'));a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('simple new label')
out=ROOT/('verification_'+a.label);out.mkdir()
result=dict(status='FAIL',hardware='MOCK_ONLY',physical_pass=False,flashed=False,serial_opened=False,old_suites_rerun=False,commands=[])
def run(args,label):
    q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (out/(label+'.log')).write_bytes(q.stdout);result['commands'].append(dict(argv=list(map(str,args)),exit_code=q.returncode,log=label+'.log'))
    if q.returncode:raise RuntimeError(label+' failed; see '+str(out/(label+'.log')))
    return q.stdout.decode('utf-8','replace')
try:
    cxx=[a.cxx]+(['c++'] if Path(a.cxx).name.lower() in ('zig','zig.exe') else [])
    for name in ('flow','app_loop'):
        args=cxx+['-std=c++17','-O1','-Wall','-Wextra','-I'+str(ROOT/'firmware/include')]
        if name=='app_loop':args+=['-I'+str(ROOT/'firmware/test/arduino_stub')]
        exe=out/(name+('.exe' if sys.platform=='win32' else ''))
        run(args+[ROOT/('tests/'+name+'.cpp'),'-o',exe],name+'_compile');result[name]=run([exe],name+'_run').strip()
    run([sys.executable,'-B',ROOT/'tests/test_jetson.py'],'jetson_tests')
    baseline=json.loads((ROOT/'BASELINE.json').read_text());unchanged=[]
    for source,digest in baseline['inputs'].items():
        relative=source.replace('\\','/').split('/include/',1)[1]
        if str(relative)=='continuous_dispense.h':continue
        assert hashlib.sha256((ROOT/'firmware/include'/relative).read_bytes()).hexdigest()==digest,str(relative)
        unchanged.append(str(relative))
    result.update(status='PASS_OFFLINE',unchanged_inherited_headers=unchanged,hx711_driver_unchanged=True)
except Exception as e:result['error']=str(e);raise
finally:(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
