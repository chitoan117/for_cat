from pathlib import Path
import os,time,json,urllib.request,sqlite3
r=Path(__file__).parent;out=r/('trial_B_'+str(int(time.time()))+'.json')
def read():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:return json.load(f)
def send(body):
 p=Path('/tmp/fc_trial_b_'+str(os.getpid())+'.txt')
 with p.open('x') as f:f.write(body+'\n')
 try:
  for _ in range(30):
   try:os.link(str(p),'/tmp/for_cat_cmd.txt');break
   except FileExistsError:time.sleep(.1)
  else:raise AssertionError('Command inbox remained busy; no command overwritten')
 finally:p.unlink()
v=read()['live']
assert v and abs(v['signed_g'])<=2 and v['bench_state'] in ('READY','MASS OK GATE?') and v['meal_phase'] in ('IDLE','FINAL','INVALID') and not v.get('dog_running') and v['inspect_required'] is False,v
result={'owner_confirmed_real_food_B_in_hopper':True,'owner_confirmed_empty_closed':True,'observation_mode':'MANUAL_TEST','manual_feed_commands_sent':0,'tare_commands_sent':0,'progress':[],'servo_open_seen':False}
send('0');time.sleep(1.5)
if read()['live'].get('selected_food')!='FOOD_B':
 request=urllib.request.Request('http://127.0.0.1:8000/api/meal-observation',data=json.dumps({'action':'SELECT_B'}).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(request,timeout=3) as f:ack=json.load(f)
 assert ack.get('queued') is True,ack
for _ in range(20):
 v=read()['live']
 if v.get('selected_food')=='FOOD_B':break
 time.sleep(.25)
else:raise AssertionError('Food selection not confirmed; remained paused')
result['selected_food_ack']=v['selected_food'];send('start\nmode')
deadline=time.monotonic()+65;last=None;started=False
while time.monotonic()<deadline:
 v=read()['live']
 entry={k:v.get(k) for k in ('bench_state','signed_g','meal_food','selected_food','meal_id','meal_phase','meal_starting_g','meal_consumed_g')}
 key=(entry['bench_state'],entry['meal_phase'])
 if key!=last:print(json.dumps(entry),flush=True);result['progress'].append(entry);last=key
 if entry['bench_state']=='CAT OPENING' and not started:started=True;result['servo_open_seen']=True;deadline=max(deadline,time.monotonic()+40)
 if started and entry['bench_state']=='CAT FAULT*':result['outcome']='SERVING_FAULT';break
 if entry['meal_phase']=='OBSERVING' and entry['meal_food']=='FOOD_B':result['outcome']='B_MEASURED_MEAL_OBSERVING';break
 time.sleep(.5)
else:result['outcome']='B_SELECTED_AWAITING_CAT' if not started else 'B_MEAL_NOT_CONFIRMED'
result['final_live']=read()['live'];out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('progress','final_live')},indent=2),flush=True)
print('Evidence: '+str(out),flush=True)
