from pathlib import Path
import json,time,statistics,urllib.request,sqlite3,os,re,math
r=Path('/home/toan/for_cat/evidence/scale_stability_20261106')
def status():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as res:return json.load(res)
def queue(text):
 target=Path('/tmp/for_cat_cmd.txt');assert not target.exists()
 tmp=Path('/tmp/forcat_settled_'+str(os.getpid())+'.txt')
 try:
  with tmp.open('x') as f:f.write(text)
  os.link(str(tmp),str(target))
 finally:tmp.unlink()
def samples(count):
 rows=[]
 for _ in range(count):
  d=status();rows.append({'at':d['esp32']['last_telemetry_at'],'g':d['weight']['grams'],'raw':d['weight']['raw_counts']});time.sleep(1)
 return rows
def collect(seconds):
 lines=[];deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
 return lines
before=samples(30);values=[x['g'] for x in before[-20:]]
span=max(values)-min(values);trend=statistics.median(values[-10:])-statistics.median(values[:10])
pre={'samples':before,'span_last20_g':span,'median_trend_g':trend}
(r/'pre_settle.json').write_text(json.dumps(pre,indent=2));print(json.dumps({'pre_span':span,'pre_trend':trend}),flush=True)
assert span<=0.8 and abs(trend)<=0.25,'Raw measurement not settled: leave automatic mode exited'
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
queue('mode\nservo_position\nweight\n');lines=collect(3)
assert any('exited=1' in x and 'servo_moving=0' in x for x in lines)
assert any('SERVO ESTIMATE=CLOSED' in x and 'inspect_lock=0' in x for x in lines)
factor=float(re.search(r'scale=([+\-\d.]+)',next(x for x in lines if 'WEIGHT =' in x)).group(1))
dbpath='/home/toan/for_cat/jetson/data/events.db'
with sqlite3.connect(dbpath,timeout=3) as db:seq=db.execute('SELECT coalesce(max(seq),0) FROM esp32_events').fetchone()[0]
queue('t\n');cal=None;deadline=time.monotonic()+15
while time.monotonic()<deadline:
 with sqlite3.connect(dbpath,timeout=3) as db:events=db.execute("SELECT body FROM esp32_events WHERE seq>? AND kind='hx_cal'",(seq,)).fetchall()
 for row in events:
  d=json.loads(row[0])
  if d.get('operation')=='rezero':cal=d
 if cal:break
 time.sleep(.2)
assert cal and cal.get('saved') and cal.get('ok')
assert math.isclose(factor,cal['counts_per_gram'],rel_tol=1e-7,abs_tol=1e-4)
after=samples(45)
result={'before':pre,'calibration':cal,'after':after,'owner_confirmed_empty_bowl':True}
(r/'settled_result.json').write_text(json.dumps(result,indent=2))
final=[x['g'] for x in after[5:]]
print(json.dumps({'after_min_g':min(final),'after_max_g':max(final),'after_last_g':final[-1]}),flush=True)
assert all(abs(x)<1.5 for x in final),'Zero drifted: leave automatic mode exited'
queue('start\nmode\nservo_position\n');resume=collect(3)
assert any('exited=0' in x and 'inspect_lock=0' in x for x in resume)
result['resume_ack']=resume;result['automatic_restored']=True
(r/'settled_result.json').write_text(json.dumps(result,indent=2));print(json.dumps({'automatic_restored':True,'ack':resume}),flush=True)
