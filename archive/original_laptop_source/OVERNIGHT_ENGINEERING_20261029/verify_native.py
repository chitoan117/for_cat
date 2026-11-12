"""Focused native builds only. Never connects to devices or runs deployment."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
HOST=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def run(args, name):
    p=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,timeout=180)
    (OUT/(name+'.log')).write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(name+' failed exit='+str(p.returncode)+'; see log')
    return p.stdout.decode('utf-8','replace')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('names',nargs='+');args=parser.parse_args()
    result={'generated_at':datetime.now().astimezone().isoformat(),'physical_pass':False,'tests':{}}
    (OUT/'native').mkdir(exist_ok=True)
    for name in args.names:
        source=OUT/('test_'+name+'.cpp')
        if not source.exists():source=FW/'test'/(name+'.cpp')
        exe=OUT/'native'/(name+'.exe')
        standard='c++14' if name in ('restart_fusion','overnight_e2e') else 'c++17'
        run([ZIG,'c++','-std='+standard,'-O1','-Wall','-Wextra','-Wpedantic','-Werror',
             '-I'+str(FW/'test/arduino_stub'),'-I'+str(FW/'include'),'-I'+str(HOST),
             '-I'+str(ROOT/'E2E_OFFLINE_DEMO_20261028'),source,'-o',exe],name+'_compile')
        if name=='current_hardware_loop':
            text=''.join(run([exe,case,OUT/('current_'+case+'_serial.log')],name+'_'+case+'_test')
                         for case in ('missing','functional','faults','buttons','held_at_boot'))
        else:
            text=run([exe,*([OUT/'production.synthetic.json'] if name=='approach_dog_loop' else [])],name+'_test')
        result['tests'][name]={'status':'PASS','standard':standard,'stdout':text,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        print(name+': PASS')
    (OUT/('native_result_'+'_'.join(args.names)+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
