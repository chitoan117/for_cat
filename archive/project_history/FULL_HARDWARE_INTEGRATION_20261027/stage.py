import json,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;c=json.loads((O/'connection.json').read_text());archive=O/'integration_stage.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for folder in ('payload','firmware'):
  for p in (O/folder).rglob('*'):
   if p.is_file() and not any(part in ('.pio','__pycache__') for part in p.parts):tar.add(p,arcname=p.relative_to(O).as_posix())
r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(archive),'toan@'+c['host']+':'+c['evidence']+'/'+archive.name],capture_output=True,timeout=120)
assert r.returncode==0,r.stderr.decode();print('Isolated stage uploaded '+str(archive.stat().st_size))
