import hashlib,json,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from ssh_run import OUT,HOST
E=json.loads((OUT/'preflight_backup_result.json').read_text())['evidence']
files=[p for p in OUT.iterdir() if p.is_file() and p.suffix in ('.py','.cjs','.md','.json','.log')]
files += [p for p in (OUT/'screenshots').glob('*') if p.suffix in ('.png','.json')]
files += [OUT/'firmware_candidate/platformio_build.log',OUT/'firmware_candidate/reference_manifest.json',OUT/'firmware_candidate/changes.json',OUT/'firmware_candidate/candidate.patch',OUT/'firmware_candidate/deploy/manifest.json']
checksums={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'client_manifest_sha256.json').write_text(json.dumps(checksums,indent=2))
archive=OUT/'client_evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in files+[OUT/'client_manifest_sha256.json']:tar.add(p,arcname=p.relative_to(OUT).as_posix())
r=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(archive),'toan@'+HOST+':'+E+'/'+archive.name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
assert r.returncode==0,r.stderr.decode();print('Client evidence uploaded; files='+str(len(files)))
