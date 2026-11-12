import hashlib,json,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;C=json.loads((O/'connection.json').read_text());P=Path(r'D:\DA_KT_NC\feeder_demo')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert '+62: All tests passed!' in (O/'flutter_tests.log').read_text()
assert '2 succeeded' in (O/'firmware_build.log').read_text()
sources={p.relative_to(P).as_posix():sha(p) for folder in ('lib','test','web','assets') for p in (P/folder).rglob('*') if p.is_file()}
for mode in ('real','mock'):
 path=O/('web_'+mode)/'forcat_build.json';m=json.loads(path.read_text());m['source_sha256']=sources;path.write_text(json.dumps(m,indent=2))
files=['config/hardware_current.json','docs/CURRENT_PROJECT_STATE.md','docs/FOUR_ULTRASONIC_20261027.md','jetson/app/device_state.py','jetson/app/system_state.py','jetson/app/ultrasonic_state.py','jetson/device/telemetry.h','jetson/device/ultrasonic_telemetry.h','jetson/device/test_ultrasonic.cpp','jetson/tests/test_ultrasonic_state.py','jetson/tests/test_system_state.py']
manifest={'files':{},'web':{},'firmware':{},'frontend_source':sources}
with tarfile.open(O/'backend_before.tar.gz') as old:
 for name in files:
  try:body=old.extractfile(name).read();before=hashlib.sha256(body).hexdigest()
  except KeyError:before=None
  manifest['files'][name]={'before':before,'after':sha(O/'payload'/name)}
manifest['web']={p.relative_to(O/'web_real').as_posix():sha(p) for p in (O/'web_real').rglob('*') if p.is_file()}
for name in ('firmware.bin','bootloader.bin','partitions.bin'):
 manifest['firmware'][name]=sha(O/'firmware/esp32/.pio/build/diag_four_ultrasonic'/name)
archive=O/'host_release.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for name in files:tar.add(O/'payload'/name,arcname='files/'+name)
 for name in manifest['web']:tar.add(O/'web_real'/name,arcname='web/'+name)
 for name in manifest['firmware']:tar.add(O/'firmware/esp32/.pio/build/diag_four_ultrasonic'/name,arcname='firmware/'+name)
manifest['archive_sha256']=sha(archive);(O/'release_manifest.json').write_text(json.dumps(manifest,indent=2))
for p in (archive,O/'release_manifest.json'):
 r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(p),'toan@'+C['host']+':'+C['evidence']+'/'+p.name],capture_output=True,timeout=180);assert r.returncode==0,r.stderr.decode()
print('Reviewed host/REAL/firmware assets uploaded; no flash')
