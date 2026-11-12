from pathlib import Path
import time,json,sqlite3,urllib.request,os,re,math
r=Path('/home/toan/for_cat/evidence/cat_gate_check_20261106')
dbpath='/home/toan/for_cat/jetson/data/events.db'
def status():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:return json.load(response)
def queue(text):
 cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists(),'Another command pending'
 tmp=Path('/tmp/forcat_recover_'+str(os.getpid())+'.txt')
 try:
  with tmp.open('x') as f:f.write(text)
  os.link(str(tmp),str(cmd))
 finally:tmp.unlink()
def collect(seconds):
 out=[];deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  out.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
 return out
before=status();assert before['esp32']['connected'] and not before['esp32']['stale']
assert before.get('bench_state') in ['READY','CAT FAULT*'],'Cycle active; do not reset'
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
queue('servo_position\nmode\nweight\n');lines=collect(3)
assert any('SERVO ESTIMATE=CLOSED' in x and 'inspect_lock=0' in x and 'moving=0' in x for x in lines),'Need physical inspection; do not clear lock'
factors=[float(re.search(r'scale=([+\-\d.]+)',x).group(1)) for x in lines if 'WEIGHT =' in x and 'scale=' in x]
assert factors
# This clears only an idle dose fault. It never clears an inspection lock or moves the gate.
queue('0\n');stopped=collect(2);assert any('EXIT 0' in x for x in stopped)
with sqlite3.connect(dbpath,timeout=3) as db:
 seq=db.execute('SELECT coalesce(max(seq),0) FROM esp32_events').fetchone()[0]
queue('t\n');cal=None;deadline=time.monotonic()+15
while time.monotonic()<deadline:
 with sqlite3.connect(dbpath,timeout=3) as db:
  events=db.execute("SELECT body FROM esp32_events WHERE seq>? AND kind='hx_cal' ORDER BY seq",(seq,)).fetchall()
 for row in events:
  d=json.loads(row[0])
  if d.get('operation')=='rezero':cal=d
 if cal:break
 time.sleep(.2)
assert cal and cal.get('ok') is True and cal.get('saved') is True
assert math.isclose(factors[-1],cal['counts_per_gram'],rel_tol=1e-7,abs_tol=1e-4)
zero=[]
for _ in range(6):
 d=status();zero.append(d['weight']['grams']);time.sleep(1)
assert all(abs(g)<1 for g in zero[-4:]),'Zero is not stable; automatic mode stays exited'
queue('start\nmode\nservo_position\n');resumed=collect(3)
assert any('DEMO STARTED:' in x for x in resumed)
assert any('exited=0' in x and 'inspect_lock=0' in x and 'servo_moving=0' in x for x in resumed)
after=status()
result={'before_state':before['bench_state'],'diagnostic':lines,'zero_grams':zero,'calibration':cal,
 'resume_ack':resumed,'after_state':after.get('bench_state'),'after_ai':after.get('ai'),
 'after_e1_cm':after.get('approach',{}).get('distance_cm'),'after_grams':after.get('grams'),
 'inspection_lock_not_overridden':True,'direct_open_close_feed_commands_sent':False}
(r/'recovery_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
