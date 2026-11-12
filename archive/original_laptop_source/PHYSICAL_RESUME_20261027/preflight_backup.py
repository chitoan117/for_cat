"""Jetson phase0: capture first, then new evidence/consistent SQLite backup only."""
import datetime,hashlib,json,os,shlex,shutil,sqlite3,subprocess,tarfile,urllib.request
from pathlib import Path
ROOT=Path('/home/toan/for_cat');PARENT=ROOT/'evidence';assert ROOT.is_dir() and PARENT.is_dir()
os.environ['GIT_OPTIONAL_LOCKS']='0'
def call(args):
 p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
 return {'argv':args,'returncode':p.returncode,'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace')}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
# All Git/status/service discovery occurs before the first evidence write.
audit={name:call(args) for name,args in {
 'git_status':['git','status','--porcelain=v1','--branch'],
 'git_diff':['git','diff','--binary'],
 'git_staged_diff':['git','diff','--cached','--binary'],
 'git_staged_files':['git','diff','--cached','--name-status'],
 'git_branch':['git','symbolic-ref','--short','HEAD'],
 'git_head':['git','rev-parse','HEAD'],
 'git_untracked':['git','ls-files','--others','--exclude-standard'],
 'services':['systemctl','--user','status','for-cat-api','for-cat-esp32-bridge','for-cat-ai','--no-pager','-l'],
 'units':['systemctl','--user','cat','for-cat-api','for-cat-esp32-bridge','for-cat-ai'],
 'api_environment':['systemctl','--user','show','for-cat-api','-p','Environment','-p','MainPID','-p','DropInPaths','-p','ExecStart'],
 'owners':['fuser','/dev/ttyACM0','/dev/video0'],
 'processes':['ps','-eo','pid,ppid,lstart,args'],
 'port':['ss','-ltnp','sport','=',':8000'],
 'journal':['journalctl','--user','-u','for-cat-api.service','-u','for-cat-esp32-bridge.service','-u','for-cat-ai.service','--since=-20min','--no-pager'],
 }.items()}
assert all(audit[n]['returncode']==0 for n in ('git_status','git_diff','git_staged_diff','git_head','git_branch'))
index=ROOT/'.git/index';index_before=digest(index)
envline=audit['api_environment']['stdout'].split('Environment=',1)[1].splitlines()[0]
env=dict(v.split('=',1) for v in shlex.split(envline) if '=' in v)
release=Path(env['FORCAT_FLUTTER_WEB_DIR']).resolve();dbpath=Path(env['DATABASE_PATH']).resolve()
assert release.is_dir() and dbpath.is_file() and release.is_relative_to(ROOT)
assert shutil.disk_usage(ROOT).free>512*1024*1024,'Insufficient space for safe backup'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
E=PARENT/('physical_resume_20261027_'+stamp);E.mkdir(mode=0o700)
(E/'audit').mkdir();(E/'backup').mkdir()
for name,value in audit.items():
 (E/'audit'/(name+'.json')).write_text(json.dumps(value,indent=2))
 (E/'audit'/(name+'.log')).write_text(value['stdout']+value['stderr'])
shutil.copy2(index,E/'backup/git_index.original');assert digest(index)==index_before
def archive(name,entries):
 def source_filter(info):
  if any(part in ('.git','.pio','.dart_tool','__pycache__') for part in Path(info.name).parts):return None
  return info
 with tarfile.open(E/'backup'/name,'w:gz') as tar:
  for path in entries:
   if path.exists():tar.add(path,arcname=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else 'user_systemd/'+path.name,filter=source_filter)
archive('backend_source_config_firmware.tar.gz',[ROOT/p for p in ('jetson/app','jetson/device','jetson/tools','jetson/tests','scripts','config','deploy','esp32','docs/CURRENT_PROJECT_STATE.md')])
archive('frontend_current.tar.gz',[release,ROOT/'frontend'])
archive('systemd_user.tar.gz',[Path('/home/toan/.config/systemd/user')])
# SQLite online backup: read-only source connection, consistent backup while telemetry continues.
dest=E/'backup/events.consistent.db'
with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=10) as source,sqlite3.connect(dest) as target:
 source.backup(target,pages=256,sleep=.05)
 integrity=target.execute('PRAGMA integrity_check').fetchone()[0]
 tables=target.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
 counts={name:target.execute(sql).fetchone()[0] for name,sql in {
  'feed_requests':'SELECT COUNT(*) FROM feed_requests',
  'feeding_records':"SELECT COUNT(*) FROM typed_records WHERE kind='feeding'",
  'feed_events':"SELECT COUNT(*) FROM events WHERE kind='FEED'"}.items()}
assert integrity=='ok'
ai_files=[ROOT/'jetson/ai/cat_dog_trt.cpp',ROOT/'jetson/ai/cat_dog_trt',ROOT/'models/tensorrt/yolov8n_320_fp16.engine',ROOT/'scripts/run_existing_ai.sh']
ai={str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in ai_files if p.is_file()}
assert len(ai)==4
(E/'audit/ai_metadata.json').write_text(json.dumps(ai,indent=2))
snapshots={}
for name,path in {'status':'/api/status','worker':'/api/meal-plans/worker','bridge':'/api/v1/esp32/status','hx_status':'/api/hx711/status','hx_calibration':'/api/hx711/calibration','plans':'/api/meal-plans'}.items():
 try:
  with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=8) as r:snapshots[name]=json.load(r)
 except Exception as error:snapshots[name]={'read_error':str(error)}
 (E/'audit'/('before_'+name+'.json')).write_text(json.dumps(snapshots[name],indent=2))
state=snapshots['status'];safety=state.get('safety',{});worker=snapshots['worker'].get('worker',{})
checks={k:safety.get(k) is False for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution')}
checks['actuator_outputs_enabled']=safety.get('actuator_outputs_enabled')==0
checks['explicit_actual_null']=snapshots['hx_status'].get('actual_dispensed_grams','MISSING') is None and worker.get('actual_dispensed_grams','MISSING') is None
checks['real']=state.get('data_source')=='REAL';checks['index_preserved']=digest(index)==index_before
summary={'evidence':str(E),'branch':audit['git_branch']['stdout'].strip(),'head':audit['git_head']['stdout'].strip(),
 'index_sha256':index_before,'current_frontend':str(release),'database':str(dbpath),'database_integrity':integrity,
 'baseline_feed_counts':counts,'safety_checks':checks,'ai_metadata':ai,'worker':worker,
 'esp32':state.get('esp32'),'ai':state.get('ai'),'ultrasonic':{k:state.get(k) for k in ('approach','water_operational')},
 'weight':state.get('weight'),'backup_complete':True}
(E/'preflight_summary.json').write_text(json.dumps(summary,indent=2))
manifest={str(p.relative_to(E)):digest(p) for p in E.rglob('*') if p.is_file()}
(E/'manifest_phase0_sha256.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(summary,indent=2))
