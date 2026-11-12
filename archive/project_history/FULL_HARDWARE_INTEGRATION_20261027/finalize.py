import hashlib,json,subprocess,tarfile
from pathlib import Path
O=Path(__file__).resolve().parent;c=json.loads((O/'connection.json').read_text());archive=O/'client_handoff.tar.gz'
selected=[p for p in O.iterdir() if p.is_file() and p.suffix in ('.py','.cjs','.md','.json','.log')]
selected += [p for p in (O/'screenshots').iterdir() if p.suffix in ('.png','.json')]
P=Path(r'D:\DA_KT_NC\feeder_demo');source={p.relative_to(P).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('lib','test','web','assets') for p in (P/folder).rglob('*') if p.is_file()}
(O/'frontend_final_sha256.json').write_text(json.dumps(source,indent=2));selected.append(O/'frontend_final_sha256.json')
with tarfile.open(archive,'w:gz') as t:
 for p in set(selected):t.add(p,arcname=p.relative_to(O).as_posix())
 for name in source:t.add(P/name,arcname='frontend_source/'+name)
r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(archive),'toan@'+c['host']+':'+c['evidence']+'/'+archive.name],capture_output=True,timeout=120);assert r.returncode==0,r.stderr.decode();print('Report, source snapshot, screenshots and logs uploaded')
