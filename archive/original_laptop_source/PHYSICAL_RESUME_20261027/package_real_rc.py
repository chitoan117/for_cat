import hashlib,json,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from ssh_run import SSH,OUT
RC=Path(r'D:\for_cat\OFFLINE_RC_20261026');WEB=RC/'web_real'
release=json.loads((RC/'release_manifest_sha256.json').read_text());pre=json.loads((OUT/'preflight_backup_result.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assets={p.relative_to(WEB).as_posix():sha(p) for p in WEB.rglob('*') if p.is_file()}
assert all(release['OFFLINE_RC_20261026/web_real/'+name]==value for name,value in assets.items())
marker=json.loads((WEB/'forcat_build.json').read_text());assert marker['mode']=='REAL' and marker['base_href']=='/flutter/' and marker['actuator_execution'] is False
archive=OUT/'rc_real_only.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name in assets:tar.add(WEB/name,arcname=name)
manifest={'mode':'REAL','archive_sha256':sha(archive),'assets':assets,'release_source':'OFFLINE_RELEASE_CANDIDATE_20261026_READY'}
(OUT/'rc_real_sha256.json').write_text(json.dumps(manifest,indent=2))
for p in (archive,OUT/'rc_real_sha256.json'):
 cmd=['scp','-o','BatchMode=yes','-o','HostKeyAlias=server-jetson.local','-i',r'C:\Users\chito\.ssh\opencode_jetson',str(p),'toan@server-jetson.local:'+pre['evidence']+'/'+p.name]
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180);assert r.returncode==0,r.stderr.decode()
print(json.dumps({'real_assets':len(assets),'archive_bytes':archive.stat().st_size,'remote_stage':pre['evidence'],'sha256':manifest['archive_sha256']},indent=2))
