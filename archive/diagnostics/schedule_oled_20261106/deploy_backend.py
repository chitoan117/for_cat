from pathlib import Path
import hashlib,sqlite3,subprocess,sys,time,json,os,urllib.request
r=Path('/home/toan/for_cat/evidence/schedule_oled_20261106');root=Path('/home/toan/for_cat/jetson')
targets={'fc_live_bridge.py':root/'tools/fc_live_bridge.py','scheduled_worker.py':root/'app/scheduled_worker.py'}
expected={'fc_live_bridge.py':'a5cdd38af602b1e135fc55541fbf1a7ea20f87b3c1a4b7a805a6e02ab13fb645','scheduled_worker.py':'b0baeaee8baf6f1c0cda106b10fc557a84643259cf329d0313c813b9f2c06134'}
api='for-cat-api.service';bridge='for-cat-esp32-bridge.service'
if sys.argv[1]=='backup':
 for name,target in targets.items():
  assert hashlib.sha256(target.read_bytes()).hexdigest()==expected[name]
  compile((r/name).read_bytes(),str(target),'exec')
 assert not (r/'events.before.db').exists()
 subprocess.run(['systemctl','--user','stop',api,bridge],check=True)
 with sqlite3.connect(root/'data/events.db') as source,sqlite3.connect(r/'events.before.db') as dest:source.backup(dest)
 print('API/bridge stopped; consistent SQLite backup saved.',flush=True)
elif sys.argv[1]=='install':
 subprocess.run(['systemctl','--user','stop',api,bridge],check=True)
 for name,target in targets.items():
  assert hashlib.sha256(target.read_bytes()).hexdigest()==expected[name]
  (r/(name+'.live.before')).write_bytes(target.read_bytes())
 try:
  for name,target in targets.items():
   temp=target.with_suffix('.py.schedule_new');temp.write_bytes((r/name).read_bytes());temp.chmod(target.stat().st_mode);temp.replace(target)
  sys.path.insert(0,str(root))
  from app.scheduled_worker import ScheduledOccurrences
  ScheduledOccurrences(root/'data/events.db')
  with sqlite3.connect(root/'data/events.db') as db:
   schema=db.execute("SELECT sql FROM sqlite_master WHERE name='scheduled_occurrences'").fetchone()[0]
   assert 'UNIQUE(plan_id,due_unix_ms)' in schema
  subprocess.run(['systemctl','--user','start',api,bridge],check=True)
 except Exception:
  for name,target in targets.items():target.write_bytes((r/(name+'.live.before')).read_bytes())
  subprocess.run(['systemctl','--user','start',api,bridge]);raise
 time.sleep(3)
 cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
 log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
 tmp=Path('/tmp/forcat_schedule_ready_'+str(os.getpid())+'.txt')
 try:
  with tmp.open('x') as f:f.write('0\ninspect_ok\nstart\nmode\nservo_position\n')
  os.link(str(tmp),str(cmd))
 finally:tmp.unlink()
 lines=[];deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
 assert any('open_ms=900' in x and 'close_ms=1450' in x and 'moving=0' in x for x in lines)
 assert any('exited=0' in x and 'inspect_lock=0' in x for x in lines)
 with sqlite3.connect(root/'data/events.db') as db:body=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
 fc=body['telemetry']['fc_live'];assert fc.get('scheduled_protocol')==1 and fc.get('ai_oled') in ['CAT','DOG','FAIL']
 result={'backend_installed':True,'slot_schema':schema,'ack':lines,'firmware':fc,'frontend_unchanged':True}
 (r/'deployment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
