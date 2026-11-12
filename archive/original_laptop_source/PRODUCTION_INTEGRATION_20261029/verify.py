"""Focused deterministic tests/builds for production integration. No devices."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
DEVICE=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
AI=ROOT/'OFFLINE_REVIEW_20261024/project/jetson/ai'
def run(args,name,timeout=180):
    p=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,timeout=timeout)
    (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr)
    print(name+': '+('PASS' if p.returncode==0 else 'FAIL'))
    if p.returncode:raise RuntimeError(name+' exit='+str(p.returncode)+'; see log')
    return p.stdout.decode('utf-8','replace')
def main():
    names=sys.argv[1:];results={}
    (HERE/'native').mkdir(exist_ok=True)
    for name in names:
        if name.endswith('.py'):
            results[name]=run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',HERE/name],Path(name).stem)
        else:
            exe=HERE/'native'/(name+'.exe')
            run([ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe','c++','-std=c++14','-O1','-pthread','-Wall','-Wextra','-Wpedantic','-Werror',
                 '-I'+str(DEVICE),'-I'+str(AI),'-I'+str(FW/'include'),'-I'+str(ROOT/'E2E_OFFLINE_DEMO_20261028'),HERE/(name+'.cpp'),'-o',exe],name+'_compile')
            results[name]=run([exe],name+'_test')
    (HERE/('result_'+'_'.join(Path(n).stem for n in names)+'.json')).write_text(json.dumps({'at':datetime.now().astimezone().isoformat(),'physical_pass':False,'results':results},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
