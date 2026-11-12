"""Offline build and copy into this session; no upload targets."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
OUT=Path(__file__).resolve().parent
FW=OUT.parent/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
profiles=sys.argv[1:]
if not profiles or any(x not in ('diag_current_hardware','diag_four_ultrasonic','cat_approach_dog_warning') for x in profiles):
    raise SystemExit('Only sensor diagnostic and locked dog-warning profiles allowed')
args=[r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',str(FW)]
for profile in profiles:args+=['-e',profile]
p=subprocess.run(args,capture_output=True,timeout=600)
(OUT/('build_'+'_'.join(profiles)+'.log')).write_bytes(p.stdout+p.stderr)
if p.returncode:raise SystemExit('Build failed; see log')
result={'physical_pass':False,'flash_performed':False,'firmware':{}}
for profile in profiles:
    target=OUT/'firmware'/profile;target.mkdir(parents=True,exist_ok=True)
    result['firmware'][profile]={}
    for name in ('firmware.bin','firmware.elf','bootloader.bin','partitions.bin'):
        source=FW/'.pio/build'/profile/name;shutil.copyfile(source,target/name)
        result['firmware'][profile][name]={'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(OUT/('build_'+'_'.join(profiles)+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('BUILD PASS: '+', '.join(profiles)+'; NOT FLASHED')
