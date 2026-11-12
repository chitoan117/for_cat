"""Focused kit tests only. Actual firmware loops run with fake GPIO/LEDC/NVS.
No serial import/open, systemctl action or upload is performed by this runner.
"""
import argparse
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
KIT=Path(__file__).resolve().parents[1];FW=KIT/'firmware';ROOT=KIT.parent
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
OUT=KIT/'test_output'
def run(argv,name,success=True,timeout=180):
    p=subprocess.run([str(x) for x in argv],cwd=KIT,capture_output=True,timeout=timeout,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'})
    (OUT/(name+'.log')).write_bytes(p.stdout+p.stderr)
    if (p.returncode==0)!=success:raise RuntimeError(name+' failed; see full log')
    return (p.stdout+p.stderr).decode('utf-8','replace')
def compiler(source,output,defines=()):
    return [ZIG,'c++','-std=c++17','-O1','-Wall','-Wextra','-Werror',
        '-I'+str(FW/'test/arduino_stub'),'-I'+str(FW/'include'),*['-D'+s for s in defines],source,'-o',output]
def native():
    result={};native_dir=OUT/'native';native_dir.mkdir(exist_ok=True)
    for name,source in [('kit_sensor_loop',KIT/'tests/kit_sensor_loop.cpp'),('kit_buzzer_loop',KIT/'tests/kit_buzzer_loop.cpp'),
                        ('kit_servo_stop',KIT/'tests/kit_servo_stop.cpp'),('quad_firmware_loop',FW/'test/quad_firmware_loop.cpp')]:
        exe=native_dir/(name+'.exe');run(compiler(source,exe),name+'_compile');result[name]=run([exe],name+'_test')
    exe=native_dir/'servo_bench_loop.exe';run(compiler(FW/'test/servo_bench_loop.cpp',exe),'servo_bench_compile')
    for case in ('cold_limits','expiry_budget','attach_fault','write_fault','hard_deadline','detach_fault','wrap_and_parser','reboot_disarms'):
        result['servo_'+case]=run([exe,case,OUT/('servo_'+case+'_serial.log')],'servo_'+case+'_test')
    for name,defines,cases in [('inert',('HOST_ACTIVE=0','HOST_OFF=-1'),('inert',)),('off0',('HOST_ACTIVE=1','HOST_OFF=0'),('bounded','reset')),
                              ('off1',('HOST_ACTIVE=1','HOST_OFF=1'),('bounded','reset'))]:
        exe=native_dir/('pump_'+name+'.exe');run(compiler(FW/'test/pump_bench_loop.cpp',exe,defines),'pump_'+name+'_compile')
        for case in cases:result['pump_'+name+'_'+case]=run([exe,case,OUT/('pump_'+name+'_'+case+'_serial.log')],'pump_'+name+'_'+case+'_test')
    base=('FORR_BOARD_S3=1','FORR_REAL_S3_NO_PSRAM=1','FORR_HW_SAFE=1','FORR_NATIVE_USB=0','ARDUINO_USB_CDC_ON_BOOT=0')
    run(compiler(KIT/'tests/guard_probe.cpp',native_dir/'valid_guard.exe',base),'valid_guard_compile')
    bad={
        'actuator_unlocked':('ACTUATOR_OUTPUTS_ENABLED=1',), 'unverified_psram':('BOARD_HAS_PSRAM=1',),
        'quad_without_station':('M4_QUAD_ULTRASONIC=1',),
        'mixed_servo_pump':('SERVO_BENCH_MODE=1','SERVO_BENCH_PHYSICAL_ENABLE=1','PUMP_BENCH_MODE=1'),
        'unknown_pump_polarity':('PUMP_BENCH_MODE=1','PUMP_BENCH_PHYSICAL_ENABLE=1','PUMP_BENCH_OFF_LEVEL=-1'),
        'pump_in_sensor_station':('PUMP_BENCH_MODE=1','M4_SENSOR_BRINGUP=1','M4_DIAGNOSTIC_MODE=7','M4_CURRENT_HARDWARE_PROFILE=1','M4_HX711_INSTALLED=1'),
    }
    for name,extra in bad.items():
        text=run(compiler(KIT/'tests/guard_probe.cpp',native_dir/(name+'.exe'),base+extra),'guard_reject_'+name,False)
        if 'error:' not in text:raise ValueError('negative compile must fail at guard, not missing tool')
    return {'loop_cases':result,'rejected_unsafe_builds':list(bad),'physical_pass':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--part',choices=('all','native','tools'),default='all');a=p.parse_args()
    OUT.mkdir(exist_ok=True);result={'at':datetime.now().astimezone().isoformat(),'physical_pass':False}
    if a.part in ('all','native'):result['native']=native()
    if a.part in ('all','tools'):
        text=run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','-o','pythonpath='+str(KIT/'tools'),KIT/'tests/test_tools.py',KIT/'tests/test_backup_recovery.py',KIT/'tests/test_physical_acceptance.py',KIT/'tests/test_hx_acceptance_record.py'],'tools_tests')
        result['python_tests']=int(re.search(r'(\d+) passed',text).group(1))
        for file in (KIT/'tools').glob('*.py'):ast.parse(file.read_text(encoding='utf-8'),str(file))
        bash=Path(r'C:\Program Files\Git\bin\bash.exe')
        if not bash.is_file():raise ValueError('Git bash required for actual shell syntax check; no shell PASS assumed')
        run([bash,'-n',KIT/'tools/bridge_flash_session.sh'],'shell_syntax')
        if (KIT/'recovery/FIRST_STEP_READONLY.sh').exists():run([bash,'-n',KIT/'recovery/FIRST_STEP_READONLY.sh'],'first_step_shell_syntax')
    (OUT/('result_'+a.part+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'offline_tests':'PASS','part':a.part,'python_tests':result.get('python_tests'),'physical_pass':False}))
if __name__=='__main__':main()
