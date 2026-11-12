"""Build/package sensor-only bounded guard tuning; upload to same milestone, no flash."""
import hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;G=O/'guard_tuning';F=G/'esp32';C=json.loads((O/'connection.json').read_text());sys.stdout.reconfigure(encoding='utf-8')
cmd=[r'C:\Users\chito\.platformio\penv\Scripts\python.exe','-m','platformio','run','--project-dir',str(F),'-e','diag_four_ultrasonic','-e','diag_current_hardware']
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=360);(G/'build.log').write_bytes(p.stdout);assert p.returncode==0,p.stdout.decode('utf-8','replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
images=G/'host_release/firmware';images.mkdir(parents=True,exist_ok=True)
for name in ('firmware.bin','bootloader.bin','partitions.bin'):shutil.copy2(F/'.pio/build/diag_four_ultrasonic'/name,images/name)
files={p.relative_to(F).as_posix():sha(p) for p in F.rglob('*') if p.is_file() and '.pio' not in p.parts}
manifest={'kind':'SENSOR_ONLY_BOUNDED_GUARD_TUNING','profile':'diag_four_ultrasonic','allowed_guard_ms':[60,80,100],
 'default_guard_ms':80,'actuator_outputs_enabled':0,'RTC':'REMOVED','physical':'NOT_TESTED_NEW_GUARD_VALUES',
 'firmware':{p.name:sha(p) for p in images.iterdir() if p.is_file()},'source_sha256':files}
(G/'release_manifest.json').write_text(json.dumps(manifest,indent=2))
archive=O/'guard_tuning_release.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in G.rglob('*'):
  if p.is_file() and '.pio' not in p.parts:tar.add(p,arcname=p.relative_to(G).as_posix())
p=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(archive),'toan@'+C['host']+':'+C['evidence']+'/'+archive.name],capture_output=True,timeout=120);assert p.returncode==0,p.stderr.decode()
print(json.dumps({'status':'SOFTWARE_READY_BUILD','images':manifest['firmware'],'source_files':len(files),'flash_performed':False},indent=2))
