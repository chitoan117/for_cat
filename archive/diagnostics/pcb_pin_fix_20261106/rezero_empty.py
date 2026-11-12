from pathlib import Path
import time,json,sqlite3,urllib.request,os,re,math
r=Path('/home/toan/for_cat/evidence/scale_rezero_20261106');r.mkdir(exist_ok=True)
dbpath='/home/toan/for_cat/jetson/data/events.db'
def status():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:return json.load(response)
def queue(text):
 cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists(),'Another command pending'
 tmp=Path('/tmp/forcat_rezero_'+str(os.getpid())+'.txt')
 try:
  with tmp.open('x') as f:f.write(text)
  os.link(str(tmp),str(cmd))
 finally:tmp.unlink()
def events(after):
 with sqlite3.connect(dbpath,timeout=3) as db:
  return db.execute('SELECT seq,kind,body FROM esp32_events WHERE seq>? ORDER BY seq',(after,)).fetchall()
before=status();assert before['esp32']['connected'] and not before['esp32']['stale']
assert before.get('bench_state')=='READY','Feeder not idle'
assert before['weight']['raw_available'] and before['weight']['firmware_calibrated']
(r/'before_status.json').write_text(json.dumps(before,indent=2))
with sqlite3.connect(dbpath,timeout=3) as db:
 seq=db.execute('SELECT coalesce(max(seq),0) FROM esp32_events').fetchone()[0]
 old=db.execute("SELECT seq,body FROM esp32_events WHERE kind='hx_cal' ORDER BY seq DESC LIMIT 10").fetchall()
(r/'previous_calibration_events.json').write_text(json.dumps(old,indent=2))
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
queue('weight\nservo_position\nmode\n')
lines=[];deadline=time.monotonic()+4
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
weight_lines=[x for x in lines if 'WEIGHT =' in x and 'counts/g' in x]
assert weight_lines,'Could not read original scale factor'
factor_before=float(re.search(r'scale=([+\-\d.]+)',weight_lines[-1]).group(1))
assert any('moving=0' in x for x in lines),'Servo not confirmed stopped'
queue('t\n') # Retare preserves factor; do not use tare (which clears calibration).
cal=None;deadline=time.monotonic()+15
while time.monotonic()<deadline:
 for _,kind,body in events(seq):
  if kind=='hx_cal':
   item=json.loads(body)
   if item.get('operation')=='rezero':cal=item
 if cal:break
 time.sleep(.2)
assert cal and cal.get('ok') is True and cal.get('saved') is True,'Retare not saved successfully'
assert math.isclose(factor_before,cal['counts_per_gram'],rel_tol=1e-7,abs_tol=1e-4),'Scale factor changed'
queue('weight\n')
samples=[]
for _ in range(10):
 d=status();samples.append({'time':d['esp32']['last_telemetry_at'],'grams':d['weight']['grams'],'raw_counts':d['weight']['raw_counts'],'connected':d['esp32']['connected']});time.sleep(1)
result={'before_grams':before['weight']['grams'],'factor_before_counts_per_g':factor_before,
 'saved_rezero':cal,'after_samples':samples,'actuator_commands_sent':False,
 'owner_confirmed_empty_scale':True}
(r/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
assert len(set(x['time'] for x in samples))>5,'Telemetry did not advance'
assert all(x['connected'] and abs(x['grams'])<1 for x in samples[-5:]),'Empty-scale reading still drifting'
