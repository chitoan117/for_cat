"""Build-only new manual+feed-inert APP; two locked images are never rebuilt."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1];BASE=WS/'HARDWARE_PHYSICAL_BRINGUP_20261029'
sys.path.insert(0,str(BASE/'tools'))
from image_layout import partitions,image_header,app_partition
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('NEW label')
out=ROOT/('dual_build_'+a.label);out.mkdir();fw=ROOT/'firmware';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
py=Path('C:/Users/chito/.platformio/penv/Scripts/python.exe');tool=Path('C:/Users/chito/.platformio/packages/tool-esptoolpy/esptool.py')
result=dict(build='FAIL',physical_pass=False,flash_executed=False,APP_FLASH='NO_GO',feed_physical_enable=False,commands=[])


def run(args,name,timeout=120):
    q=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,
        env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'})
    (out/(name+'.log')).write_bytes(q.stdout);result['commands'].append(dict(command=[str(x) for x in args],timestamp_utc=datetime.now(timezone.utc).isoformat(),exit_code=q.returncode,log=name+'.log'))
    if q.returncode:raise RuntimeError(name+' failed; preserve evidence')


try:
    run([py,'-m','platformio','run','--project-dir',fw,'-e','dual_station_safe'],'compile',1200)
    built=fw/'.pio/build/dual_station_safe';meta=json.loads((built/'flash_layout.json').read_text());image=built/'firmware.bin'
    table=built/'partitions.bin';assert table.read_bytes()==(BASE/'artifacts/diag_four_ultrasonic/partitions.bin').read_bytes()
    layout=partitions(table.read_bytes());offset=int(meta['application_offset'],0);app=app_partition(layout,offset)
    header=image_header(image.read_bytes()[:24]);assert header['flash_size_code']==4 and image.stat().st_size<=app['size']
    assert 'BOARD_HAS_PSRAM' not in repr(meta['cppdefines']) and 'MANUAL_STATION_HOST_TEST' not in repr(meta['cppdefines'])
    assert 'feed_warning,false)' in (fw/'src/dual_station.cpp').read_text()
    run([py,tool,'--chip','esp32s3','image-info',image],'image_info')
    artifacts=out/'artifacts';artifacts.mkdir()
    for name in ('firmware.bin','firmware.elf'):shutil.copyfile(built/name,artifacts/name)
    for path,digest in json.loads((ROOT/'BASELINE.json').read_text())['locked_images'].items():assert sha(Path(path))==digest
    result.update(build='PASS_OFFLINE',image=str(artifacts/'firmware.bin'),image_bytes=image.stat().st_size,image_sha256=sha(image),
        build_app_offset=offset,actual_running_bank='NOT_VERIFIED',partition_table_unchanged=True,header=header,metadata=meta,
        source_sha256={p.relative_to(fw).as_posix():sha(p) for d in ('src','include') for p in (fw/d).rglob('*') if p.is_file()})
except Exception as e:result['error']=str(e);raise
finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('build','image','image_bytes','image_sha256','feed_physical_enable','APP_FLASH')},indent=2))
