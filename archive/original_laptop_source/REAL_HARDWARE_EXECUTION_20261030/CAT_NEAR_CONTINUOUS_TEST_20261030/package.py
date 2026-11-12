"""Build evidence/package only: no device or uploader. Refuses existing outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
if not a.label.replace('_','').isalnum():p.error('new simple label')
evidence=ROOT/('evidence_'+a.label);evidence.mkdir()
pio=Path(r'C:\Users\chito\.platformio\penv\Scripts\python.exe')
q=subprocess.run([str(pio),'-m','platformio','run','-e','cat_continuous_test'],cwd=ROOT/'firmware',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
(evidence/'esp32_build.log').write_bytes(q.stdout)
if q.returncode:raise RuntimeError('ESP32 build failed')
zig=ROOT.parents[1]/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
q=subprocess.run([str(zig),'c++','-target','aarch64-linux-gnu','-std=c++17','-Wall','-Wextra','-Werror','-c',str(ROOT/'tests/ai_hook.cpp'),'-o',str(evidence/'ai_hook_arm64.o')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(evidence/'ai_hook_arm64_syntax.log').write_bytes(q.stdout)
if q.returncode:raise RuntimeError('AI hook ARM64 syntax failed')
build=ROOT/'firmware/.pio/build/cat_continuous_test'
artifacts=ROOT/'artifacts';artifacts.mkdir()
for name in ('firmware.bin','flash_layout.json'):shutil.copyfile(build/name,artifacts/name)
v=json.loads((ROOT/'verification_final/RESULT.json').read_text())
assert v['status']=='PASS_OFFLINE'
result=dict(status='PASS_OFFLINE',firmware_build='ESP32-S3_SUCCESS',physical_pass=False,flashed=False,serial_opened=False,
    jetson_arm64_runtime='NOT_RUN',ai_hook_arm64='OBJECT_COMPILE_ONLY_PASS',flow=v['flow'],actual_app_loop=v['app_loop'],python_test_cases=12,
    hx711_driver_unchanged=True,unchanged_inherited_headers=len(v['unchanged_inherited_headers']),automatic_mode=False,
    default_configuration='UNSET_CANNOT_ARM',application_bytes=(artifacts/'firmware.bin').stat().st_size,
    application_sha256=hashlib.sha256((artifacts/'firmware.bin').read_bytes()).hexdigest(),old_suites_rerun=False)
(ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
files=[]
for path in ROOT.rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(ROOT)
    if any(part in ('.pio','__pycache__') for part in rel.parts) or path.suffix in ('.exe','.zip') or rel.name in ('MANIFEST.json','PACKAGE.json'):continue
    # Keep only stubs/support from the inherited historical test tree.
    if rel.parts[:2]==('firmware','test') and 'arduino_stub' not in rel.parts and rel.name!='ds1302_fake_pins.h':continue
    files.append((path,rel.as_posix()))
manifest={rel:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p,rel in files}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');files.append((ROOT/'MANIFEST.json','MANIFEST.json'))
archive=ROOT/'FOR_CAT_CONTINUOUS_25G_COMPLETE.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for path,rel in sorted(files,key=lambda x:x[1]):z.write(path,ROOT.name+'/'+rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for rel,meta in manifest.items():assert hashlib.sha256(z.read(ROOT.name+'/'+rel)).hexdigest()==meta['sha256'],rel
meta=dict(zip=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),payload_files=len(files),round_trip_hashes='PASS')
(ROOT/'PACKAGE.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(dict(result=result,package=meta),indent=2))
