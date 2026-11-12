"""Windows-only software verification; no SSH, hardware, camera or real serial."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT/'project'
LOG=OUT/'checks'
LOG.mkdir(exist_ok=False)
ZIG=Path(r'D:\for_cat\.tools-zig\zig-x86_64-windows-0.16.0\zig.exe')
records=[]
def run(name,command,timeout=120):
    result=subprocess.run([str(x) for x in command],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          timeout=timeout,env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'jetson'),str(ROOT)])})
    (LOG/(name+'.log')).write_bytes(result.stdout)
    records.append({'name':name,'command':[str(x) for x in command],'exit_code':result.returncode})
    (LOG/'commands.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(result.stdout.decode('utf-8','replace'),flush=True)
    if result.returncode:raise SystemExit(name+' FAILED')

tests=['jetson/tests/test_device_state_api.py','jetson/tests/test_system_state.py',
       'jetson/tests/test_dry_run_requests.py','jetson/tests/test_schedule_gate.py',
       'jetson/tests/test_state_cache_resilience.py','jetson/tests/test_api.py',
       'jetson/tests/test_release_api_contract.py','jetson/tests/test_real_transport.py']
run('python_api_state_contracts',[sys.executable,'-m','pytest',*tests,'-q','-ra'])
run('ruff',[sys.executable,'-m','ruff','check','jetson/app/device_state.py','jetson/app/ai_state.py',
            'jetson/app/system_state.py','jetson/tests/test_device_state_api.py',
            'jetson/tests/test_system_state.py','jetson/tests/test_state_cache_resilience.py'])
flags=['c++','-std=c++14','-O1','-fsanitize=undefined','-fno-sanitize-recover=undefined',
       '-Wall','-Wextra','-Wpedantic','-Werror','-Iesp32/include']
for name,source in [('decision','jetson/device/test_decision.cpp'),
                    ('dispense_policy','esp32/test/dispense_policy.cpp'),
                    ('dispense_35','jetson/device/test_dispense_35.cpp')]:
    binary=LOG/(name+'.exe')
    run(name+'_build',[ZIG,*flags,source,'-o',binary])
    run(name,[binary],timeout=30)
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scope':'OFFLINE_WINDOWS_SOFTWARE_ONLY','jetson_connection_used':False,
         'physical_tests_performed':False,'firmware_flash_performed':False,
         'linux_bridge_build':'NOT_RUN_REQUIRES_JETSON','linux_tty_reconnect':'NOT_RUN_REQUIRES_LINUX_PTY',
         'commands':records}
(LOG/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('OFFLINE_CHECKS_PASS',LOG)
