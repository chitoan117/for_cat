"""Focused offline tests/build artifacts only. Never opens serial/camera or flashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import argparse

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
HOST=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
def run(cmd,name,timeout=360):
 p=subprocess.run([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (OUT/name).write_bytes(p.stdout)
 if p.returncode:raise RuntimeError(p.stdout.decode('utf-8','replace'))
 return p.stdout.decode('utf-8','replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--tests-only',action='store_true');parser.add_argument('--only',action='append');args=parser.parse_args()
 (OUT/'native').mkdir(exist_ok=True)
 result={'kind':'CAT_APPROACH_DOG_BUZZER_FOCUSED','physical':'NOT_TESTED','servo':'LOCKED','pump':'LOCKED',
         'hx711_authority':'PHYSICAL_VALIDATION_PENDING','tests':[],'generated_utc':datetime.now(timezone.utc).isoformat()}
 for name in ('approach_dog_cases','approach_dog_loop','dog_buzzer_diag_loop','quad_firmware_loop'):
  if name=='quad_firmware_loop' and not args.only:continue
  if args.only and name not in args.only:continue
  exe=OUT/'native'/(name+'.exe')
  run([ZIG,'c++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-I'+str(FW/'test/arduino_stub'),'-I'+str(FW/'include'),'-I'+str(HOST),FW/'test'/(name+'.cpp'),'-o',exe],name+'_compile.log')
  text=run([exe,*([OUT/'production.synthetic.json'] if name=='approach_dog_loop' else [])],name+'_test.log');print(text)
  result['tests'].append({'name':name,'status':'PASS','stdout':text})
 if args.tests_only:
  previous=json.loads((OUT/'result.json').read_text(encoding='utf-8'))
  for item in previous['tests']:
   if item['name'] not in {test['name'] for test in result['tests']}:
    log=OUT/(item['name']+'_test.log')
    if log.exists():item={**item,'stdout':log.read_text(encoding='utf-8')}
    result['tests'].append(item)
  result['firmware']=previous['firmware'];result['firmware_reused_unchanged']=True
  for profile,items in result['firmware'].items():
   for name,metadata in items.items():assert sha(OUT/'firmware'/profile/name)==metadata['sha256']
  result['hx711_source_sha256']={name:sha(FW/'include/m4'/name) for name in ('hx711.h','hx711_reference.h','calibration.h','calibration_record.h')}
  assert result['hx711_source_sha256']==previous['hx711_source_sha256']
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return
 run([r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',FW,'-e','cat_approach_dog_warning','-e','diag_dog_buzzer'],'firmware_build.log',600)
 result['firmware']={}
 for profile in ('cat_approach_dog_warning','diag_dog_buzzer'):
  target=OUT/'firmware'/profile;target.mkdir(parents=True,exist_ok=True);result['firmware'][profile]={}
  for name in ('firmware.bin','firmware.elf','bootloader.bin','partitions.bin'):
   source=FW/'.pio/build'/profile/name;shutil.copyfile(source,target/name)
   result['firmware'][profile][name]={'sha256':sha(source),'bytes':source.stat().st_size}
 result['hx711_source_sha256']={name:sha(FW/'include/m4'/name) for name in ('hx711.h','hx711_reference.h','calibration.h','calibration_record.h')}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'focused':'PASS','firmware':'PASS','physical':'NOT_TESTED'}))
if __name__=='__main__':main()
