"""Build-only Windows artifacts. Never invokes upload/erase/serial/device APIs."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from image_layout import FLASH_SIZE,sha,partitions,image_header,app_partition

KIT=Path(__file__).resolve().parents[1];ROOT=KIT.parent;FW=KIT/'firmware'
PIO=Path(r'C:\Users\chito\.platformio\penv\Scripts\python.exe')
ESPTOOL=Path(r'C:\Users\chito\.platformio\packages\tool-esptoolpy\esptool.py')
DEFAULT=('diag_four_ultrasonic','diag_dog_buzzer','diag_servo_bench','diag_pump_bench')
LOG_DIR=KIT/'build_logs'
def run(args,name,timeout=120):
    env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
    p=subprocess.run([str(x) for x in args],cwd=KIT,env=env,capture_output=True,timeout=timeout)
    (LOG_DIR/name).write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(name+' failed; full log retained')
    return p.stdout.decode('utf-8','replace')
def pump_variant(off_level,observation):
    if off_level not in (0,1) or observation is None:raise ValueError('explicit observed off-level and evidence file required')
    data=json.loads(Path(observation).read_text(encoding='utf-8'));observed=data.get('USER_OBSERVED',{})
    if type(observed.get('f5305s_off_level')) is not int or observed['f5305s_off_level']!=off_level or observed.get('boot_off_verified') is not True or not observed.get('observer'):
        raise ValueError('owner observation must include same measured OFF level and boot OFF review; not software ACK')
    return 'diag_pump_bench_active_high' if off_level==0 else 'diag_pump_bench_active_low'
def main():
    global LOG_DIR
    p=argparse.ArgumentParser();p.add_argument('--pump-off-level',type=int,choices=(0,1));p.add_argument('--observation',type=Path);a=p.parse_args()
    profiles=list(DEFAULT)
    if a.pump_off_level is not None:
        profiles=[pump_variant(a.pump_off_level,a.observation)]
        LOG_DIR=KIT/'conditional_logs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    LOG_DIR.mkdir(parents=True,exist_ok=True)
    result={'kind':'WINDOWS_PHYSICAL_TEST_KIT_BUILD','physical_pass':False,'flash_performed':False,
        'python':run([PIO,'--version'],'python_version.log').strip(),
        'platformio':run([PIO,'-m','platformio','--version'],'platformio_version.log').strip(),
        'esptool':run([PIO,ESPTOOL,'version'],'esptool_version.log').strip(),'profiles':{},
        'pump_polarity_selected':a.pump_off_level,'uart_contract':'UART0_115200_NOT_INFERRED_FROM_TTY_NAME'}
    command=[PIO,'-m','platformio','run','--project-dir',FW]
    for name in profiles:command+=['-e',name]
    run(command,'platformio_build.log',1200)
    for profile in profiles:
        build=FW/'.pio/build'/profile
        raw=json.loads((build/'flash_layout.json').read_text(encoding='utf-8'))
        offset=int(raw['application_offset'],0)
        extras=[{**x,'offset':int(x['offset'],0)} for x in raw['extra_images']]
        table_item=next(x for x in extras if Path(x['file']).name=='partitions.bin')
        table=partitions(Path(table_item['file']).read_bytes())
        app=app_partition(table,offset);image=build/'firmware.bin'
        if image.stat().st_size>app['size']:raise ValueError('app does not fit selected partition')
        header=image_header(image.read_bytes()[:24])
        if header['flash_size_code']!=4:raise ValueError('built image does not declare16MB')
        defs=repr(raw['cppdefines'])
        if 'BOARD_HAS_PSRAM' in defs or 'FORR_REAL_S3_NO_PSRAM' not in defs:raise ValueError('PSRAM/board guard mismatch')
        target=KIT/('artifacts' if a.pump_off_level is None else 'conditional_artifacts')/profile;target.mkdir(parents=True,exist_ok=True)
        artifacts={}
        for source,address,role in [(image,offset,'APPLICATION_ONLY_DEFAULT'),(build/'firmware.elf',None,'ELF_DEBUG')]+[(Path(x['file']),x['offset'],'BOOT_COMPONENT_INSPECT_ONLY') for x in extras]:
            dest=target/source.name;shutil.copyfile(source,dest)
            artifacts[dest.name]={'sha256':sha(dest),'bytes':dest.stat().st_size,'offset':address,'role':role}
        run([PIO,ESPTOOL,'--chip','esp32s3','image-info',image],profile+'_image_info.log')
        boot=next(x for x in extras if Path(x['file']).name=='bootloader.bin')
        image_header(Path(boot['file']).read_bytes()[:24])
        layout={'profile':profile,'board':'ESP32-S316MB_NO_VERIFIED_PSRAM','build_metadata':raw,
            'app_offset':offset,'bootloader_offset':boot['offset'],'partition_table_offset':table_item['offset'],
            'partitions':table,'application_partition':app,'flash_size':FLASH_SIZE,'artifacts':artifacts,
            'physical_pass':False,'factory_image_excluded':True,'default_flash_policy':'APP_ONLY_AFTER_FULL_BACKUP_AND_MATCHING_EXISTING_LAYOUT'}
        (target/'layout.json').write_text(json.dumps(layout,indent=2)+'\n',encoding='utf-8')
        result['profiles'][profile]=layout
    project_files=[FW/'platformio.ini',FW/'kit_metadata.py']+[x for directory in ('src','include') for x in (FW/directory).rglob('*') if x.is_file()]
    result['firmware_source_sha256']={x.relative_to(FW).as_posix():sha(x) for x in project_files}
    result_name='build_result.json' if a.pump_off_level is None else 'conditional_pump_build_off'+str(a.pump_off_level)+'.json'
    (KIT/result_name).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'build':'PASS','profiles':profiles,'physical_pass':False,'flashed':False}))
if __name__=='__main__':main()
