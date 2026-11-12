"""Only inox-bowl related offline tests/builds. No SSH, serial open or flash."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
HOST=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,name,timeout=180):
    p=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    (OUT/name).write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(p.stdout.decode('utf-8','replace'))
    return p.stdout.decode('utf-8','replace')

def main():
    old=json.loads((ROOT/'HX711_REFERENCE_PORT_20261028/result.json').read_text(encoding='utf-8'))
    for name in ('hx711.h','hx711_reference.h','calibration.h','calibration_record.h'):
        assert sha(FW/'include/m4'/name)==old['source_sha256']['include/m4/'+name]
    live=json.loads((ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028/verification.json').read_text(encoding='utf-8'))
    for name,digest in live['backend_source_sha256'].items():assert sha(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'/name)==digest
    for name,digest in live['frontend_source_sha256'].items():assert sha(Path(r'D:\DA_KT_NC\feeder_demo')/name)==digest
    text=run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',OUT/'test_bowl_mass.py'],'bowl_tests.log')
    print(text)
    if '--tests-only' in sys.argv:
        result=json.loads((OUT/'result.json').read_text(encoding='utf-8'));result['software_tests']=text
        result['source_sha256'][str((ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/hx711_view.py').relative_to(ROOT))]=sha(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/hx711_view.py')
        result['source_sha256'][str((OUT/'bowl_log.py').relative_to(ROOT))]=sha(OUT/'bowl_log.py')
        for name,meta in result['firmware'].items():assert sha(OUT/'firmware/diag_hx711_inox'/name)==meta['sha256']
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return
    (OUT/'native').mkdir(exist_ok=True)
    result={'software_tests':text,'hardware_pass':False,'physical_result':'PENDING_OWNER_LOGS','ssh_used':False,'serial_opened':False,'flash_performed':False,
            'servo':'LOCKED','pump':'LOCKED','hx_reader_algorithm_unchanged':True,'live_camera_frontend_unchanged':True,'native_tests':{}}
    for name,source,std in [('hx711_inox_loop',FW/'test/hx711_inox_loop.cpp','c++17'),
                            ('hx711_reference_loop',FW/'test/hx711_reference_loop.cpp','c++17'),
                            ('test_inox_e2e',OUT/'test_inox_e2e.cpp','c++14')]:
        exe=OUT/'native'/(name+'.exe')
        run([ZIG,'c++','-std='+std,'-O1','-Wall','-Wextra','-Wpedantic','-Werror','-I'+str(FW/'test/arduino_stub'),'-I'+str(FW/'include'),'-I'+str(HOST),'-I'+str(ROOT/'E2E_OFFLINE_DEMO_20261028'),source,'-o',exe],name+'_compile.log')
        output=run([exe],name+'_test.log')
        if name=='test_inox_e2e':
            rows=[json.loads(line) for line in output.splitlines()]
            selected=[row for row in rows if row['kind'] in ('INOX_E2E_RESULT','INOX_LEFTOVER_RESULT')]
            assert len(selected)==2 and all(row['status']=='PASS' and row['simulation'] is True and row['production_actuator_execution'] is False for row in selected)
            result['native_tests'][name]=selected;print(name+': PASS (SIMULATED inox95 -> gross130, delta35, consumed30)')
        else:result['native_tests'][name]=output;print(output.splitlines()[-1])
    run([r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',FW,'-e','diag_hx711_inox','-e','diag_hx711_reference'],'firmware_build.log',600)
    target=OUT/'firmware/diag_hx711_inox';target.mkdir(parents=True,exist_ok=True)
    result['firmware']={}
    for name in ('firmware.bin','firmware.elf','bootloader.bin','partitions.bin'):
        source=FW/'.pio/build/diag_hx711_inox'/name;shutil.copyfile(source,target/name)
        result['firmware'][name]={'sha256':sha(source),'bytes':source.stat().st_size}
    result['source_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [FW/'src/hx711_reference_diag.cpp',FW/'include/m4/inox_mount_binding.h',FW/'platformio.ini',
       ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/bowl_mass.py',ROOT/'E2E_OFFLINE_DEMO_20261028/sim_support.h',OUT/'bowl_log.py']}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'software':'PASS','firmware':'PASS','physical':'PENDING_OWNER_LOGS','servo':'LOCKED','pump':'LOCKED'}))
if __name__=='__main__':main()
