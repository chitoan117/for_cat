"""Build NEW INERT protocol firmware only; never enables/flashes physical outputs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
BASE=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029'
sys.path.insert(0,str(BASE/'tools'))
from image_layout import partitions,image_header,app_partition
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('firmware_build_'+a.label);out.mkdir();fw=ROOT/'firmware'
py=Path('C:/Users/chito/.platformio/penv/Scripts/python.exe')
esptool=Path('C:/Users/chito/.platformio/packages/tool-esptoolpy/esptool.py')
result={'build':'FAIL','physical_pass':False,'flashed':False,'APP_FLASH':'NO_GO','physical_enable':False,'commands':[]}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def run(args,label,timeout=120):
    row={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'command':[str(x) for x in args]}
    q=subprocess.run(row['command'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,
        env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'})
    (out/(label+'.log')).write_bytes(q.stdout);row.update(exit_code=q.returncode,log=label+'.log');result['commands'].append(row)
    if q.returncode:raise RuntimeError(label+' failed, preserve output')


try:
    run([py,'-m','platformio','run','--project-dir',fw,'-e','feed_link_inert'],'compile',1200)
    built=fw/'.pio/build/feed_link_inert';meta=json.loads((built/'flash_layout.json').read_text())
    assert '-DFORCAT_FEED_PHYSICAL_ENABLE=0' in meta['build_flags'] and '-DFORCAT_FEED_BUZZER_ENABLE=0' in meta['build_flags']
    assert 'BOARD_HAS_PSRAM' not in repr(meta['cppdefines'])
    table=built/'partitions.bin';assert table.read_bytes()==(BASE/'artifacts/diag_four_ultrasonic/partitions.bin').read_bytes()
    layout=partitions(table.read_bytes());offset=int(meta['application_offset'],0);app=app_partition(layout,offset)
    image=built/'firmware.bin';header=image_header(image.read_bytes()[:24]);assert header['flash_size_code']==4 and image.stat().st_size<=app['size']
    assert struct.unpack_from('<I',image.read_bytes(),32)[0]==0xabcd5432
    run([py,esptool,'--chip','esp32s3','image-info',image],'image_info')
    artifacts=out/'artifacts';artifacts.mkdir()
    for name in ('firmware.bin','firmware.elf'):shutil.copyfile(built/name,artifacts/name)
    result.update(build='PASS_OFFLINE',image=str(artifacts/'firmware.bin'),image_sha256=sha(image),image_bytes=image.stat().st_size,
        secure_version=struct.unpack_from('<I',image.read_bytes(),36)[0],header=header,build_app_offset=offset,
        actual_running_offset='NOT_VERIFIED',partition_table_unchanged=True,build_metadata=meta,
        hardened_controller_sha256=sha(fw/'include/m4/dispense_bench.h'),
        source_sha256={p.relative_to(fw).as_posix():sha(p) for d in ('include','src') for p in (fw/d).rglob('*') if p.is_file()})
except Exception as e:result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('build','image','image_sha256','image_bytes','physical_enable','APP_FLASH')},indent=2))
