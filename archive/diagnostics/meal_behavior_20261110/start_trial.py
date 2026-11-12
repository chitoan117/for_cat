from pathlib import Path
import os,time,json,urllib.request,sqlite3
r=Path(__file__).parent;request_id='owner_trial_A_'+str(int(time.time()))
def live():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=3) as f:
  return json.load(f)['live']
def send(body):
 p=Path('/tmp/fc_meal_trial_'+str(os.getpid())+'.txt')
 with p.open('x') as f:f.write(body+'\n')
 try:os.link(str(p),'/tmp/for_cat_cmd.txt')
 finally:p.unlink()
v=live();assert v and v['meal_phase']=='IDLE',v
assert abs(v['signed_g'])<=2 and v['bench_state']=='READY' and not v.get('dog_running'),v
assert v['selected_food']=='FOOD_A' and abs(v['tare_counts']+699593)<.001,v
# Owner confirmed: empty bowl, gate aligned CLOSED, servo powered, FOOD_A ready, observing in person.
result={'request_id':request_id,'owner_confirmed_physical_closed':True,'food':'FOOD_A','request_sent':False,'progress':[]}
try:
 send('pump_off\na\ninspect_ok\nstart\nfeed_once '+request_id)
 result['request_sent']=True
 deadline=time.monotonic()+65;previous=None
 while time.monotonic()<deadline:
  v=live()
  if v:
   item={k:v.get(k) for k in ('bench_state','signed_g','meal_id','meal_phase','meal_starting_g','meal_remaining_g','meal_preference')}
   state=(item['bench_state'],item['meal_phase'])
   if state!=previous:result['progress'].append(item);print(json.dumps(item),flush=True);previous=state
   if v['meal_phase']=='OBSERVING':result['outcome']='MEASURED_MEAL_OBSERVING';break
   if v['meal_phase']=='INVALID' or v['bench_state']=='CAT FAULT*':result['outcome']='CHECK_PHYSICAL_SERVING';break
  time.sleep(.5)
 else:result['outcome']='NO_OBSERVATION_STARTED'
 if result['outcome']!='MEASURED_MEAL_OBSERVING':send('0')
finally:
 with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db') as db:
  result['native_events']=[json.loads(x[0]) for x in db.execute("SELECT body FROM esp32_events WHERE kind IN ('scheduled_ack','scheduled_result') ORDER BY seq DESC LIMIT 12") if json.loads(x[0]).get('request_id')==request_id]
 (r/'trial_A_start.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2),flush=True)
