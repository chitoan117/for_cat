"""Only changed actual-app diagnostics tests and single-file compile. No UART."""
import json
import subprocess
import sys
from pathlib import Path
R=Path(__file__).resolve().parent;out=R/'verification_raw';out.mkdir()
def run(args,name,cwd=R):
    q=subprocess.run(list(map(str,args)),cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    (out/(name+'.log')).write_bytes(q.stdout)
    if q.returncode:raise RuntimeError(name+' failed')
    return q.stdout.decode('utf-8','replace').strip()
run([sys.executable,'-B',R/'make_arduino.py'],'amalgamate')
zig=R.parents[1]/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
run([zig,'c++','-std=c++17','-O1','-Wall','-Wextra','-I'+str(R/'firmware/include'),'-I'+str(R/'firmware/test/arduino_stub'),R/'tests/app_loop.cpp','-o',out/'app.exe'],'app_compile')
checks=run([out/'app.exe'],'app_run')
run([r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','-e','arduino_single'],'esp32_single_build',R/'firmware')
result=dict(status='PASS_OFFLINE',actual_app_loop=checks,single_file_build='PASS',serial_opened=False,flashed=False,calibration_written=False,physical_pass=False)
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
