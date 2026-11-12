from pathlib import Path
import os,time,json,urllib.request,sqlite3
r=Path(__file__).parent;out=r/('clean_retest_'+str(int(time.time()))+'.json')
def live():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:return json.load(f)['live']
def send(body):
 p=Path('/tmp/fc_clean_retest_'+str(os.getpid())+'.txt')
 with p.open('x') as f:f.write(body+'\n')
 try:os.link(str(p),'/tmp/for_cat_cmd.txt')
 finally:p.unlink()
v=live()
assert v and v['inspect_required'] is False and v['bench_state'] in ('READY','CAT FAULT*') and not v.get('dog_running'),v
assert abs(v['signed_g'])<=2 and v['meal_phase']=='IDLE',v
result={'owner_confirmed_empty_closed_ready':True,'prior_cycle_touch_confirmed':True,'manual_feed_commands_sent':0,'tare_commands_sent':0,'servo_open_seen':False,'progress':[]}
send('0\nstart\nmode') # Clear only the previous overload fault after owner-confirmed recovery.
deadline=time.monotonic()+65;prev=None;started=False
while time.monotonic()<deadline:
 v=live()
 with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db') as db:
  a=json.loads(db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()[0])
  b=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
 sensor=(b.get('telemetry') or {}).get('sensors',{}).get('approach') or {}
 fresh=a.get('host_boot_id')==b.get('host_boot_id') and 0<=time.monotonic()*1000-a.get('updated_monotonic_ms',0)<2500
 cm=sensor.get('distance_cm') if sensor.get('distance_valid') else None
 entry={k:v.get(k) for k in ('bench_state','signed_g','demo_exited','device_feed_block_reason','meal_id','meal_phase','meal_starting_g','meal_consumed_g')}
 entry.update(ai=a.get('classification') if fresh else 'STALE',confidence=a.get('confidence') if fresh else None,E1_cm=cm)
 key=(entry['bench_state'],entry['demo_exited'],entry['meal_phase'],entry['ai'],isinstance(cm,(int,float)) and cm<=30)
 if key!=prev:print(json.dumps(entry),flush=True);result['progress'].append(entry);prev=key
 if entry['bench_state']=='CAT OPENING' and not started:
  result['servo_open_seen']=True;started=True;deadline=max(deadline,time.monotonic()+40)
 if started and entry['bench_state']=='CAT FAULT*':result['outcome']='SERVING_FAULT';break
 if started and entry['meal_phase']=='OBSERVING':result['outcome']='AUTO_CYCLE_AND_MEASURED_MEAL';break
 time.sleep(.5)
else:result['outcome']='WAITING_FOR_CAT' if not started else 'MEAL_NOT_YET_CONFIRMED'
result['final_live']=live();out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('progress','final_live')},indent=2),flush=True)
print('Evidence: '+str(out),flush=True)
