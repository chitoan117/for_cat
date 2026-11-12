import difflib,hashlib,json,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from ssh_run import OUT,HOST
F=OUT/'firmware_candidate';S=F/'esp32';ref=json.loads((F/'reference_manifest.json').read_text());base=Path(ref['reference_root'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changes={};patch=[]
for p in S.rglob('*'):
 if not p.is_file() or '.pio' in p.parts:continue
 name=p.relative_to(S).as_posix();old=ref['reference_source_sha256'].get(name)
 if sha(p)==old:continue
 changes[name]='MODIFIED' if old else 'ADDED'
 if p.suffix in ('.cpp','.h','.ini'):
  patch.extend(difflib.unified_diff((base/name).read_text().splitlines(keepends=True) if old else [],p.read_text().splitlines(keepends=True),fromfile='reference/'+name,tofile='candidate/'+name))
(F/'candidate.patch').write_text(''.join(patch));(F/'changes.json').write_text(json.dumps(changes,indent=2))
D=F/'deploy';D.mkdir(exist_ok=True)
for name in ('firmware.bin','bootloader.bin','partitions.bin'):
 source=S/'.pio/build/diag_four_ultrasonic'/name;assert source.is_file()
 import shutil;shutil.copy2(source,D/name)
(D/'manifest.json').write_text(json.dumps({'status':'SOFTWARE_READY_UNFLASHED','physical':'NOT_TESTED','actuators_enabled':False,'pins':'PROPOSED_NOT_YET_PHYSICAL_VERIFIED','files':{p.name:sha(p) for p in D.iterdir() if p.suffix=='.bin'}},indent=2))
tarpath=OUT/'firmware_candidate_r2.tar.gz'
with tarfile.open(tarpath,'w:gz') as tar:
 for p in F.rglob('*'):
  if p.is_file() and '.pio' not in p.parts:tar.add(p,arcname=p.relative_to(F).as_posix())
E=json.loads((OUT/'preflight_backup_result.json').read_text())['evidence']
p=subprocess.run(['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(tarpath),'toan@'+HOST+':'+E+'/'+tarpath.name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
assert p.returncode==0,p.stderr.decode();print(json.dumps({'changes':changes,'candidate_archive_sha256':sha(tarpath)},indent=2))
