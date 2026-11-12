from pathlib import Path
import os,time,json,urllib.request
r=Path(__file__).parent;out=r/('pause_select_B_'+str(int(time.time()))+'.json')
def read():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:return json.load(f)
def send(body):
 p=Path('/tmp/fc_pause_b_'+str(os.getpid())+'.txt')
 with p.open('x') as f:f.write(body+'\n')
 try:os.link(str(p),'/tmp/for_cat_cmd.txt')
 finally:p.unlink()
before=read();v=before['live'];assert v['bench_state'] in ('MASS OK GATE?','READY','CAT FAULT*') and not v.get('dog_running'),v
send('pump_off\n0\nmode');time.sleep(2)
request=urllib.request.Request('http://127.0.0.1:8000/api/meal-observation',data=b'{"action":"SELECT_B"}',headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(request,timeout=3) as f:ack=json.load(f)
for _ in range(20):
 after=read();live=after['live']
 if live['selected_food']=='FOOD_B' and live['demo_exited'] is True:break
 time.sleep(.25)
else:raise AssertionError('Paused foodB state not confirmed')
result={'before':before,'select_ack':ack,'after':after,'active_A_meal_interrupted_for_label_switch':v.get('meal_phase')=='OBSERVING','no_movement_commands_sent':True}
out.write_text(json.dumps(result,indent=2))
print(json.dumps({'paused':live['demo_exited'],'selected_food':live['selected_food'],'signed_g':live['signed_g'],'meal_phase':live['meal_phase'],'previous_meal_id':v.get('meal_id'),'evidence':str(out)}),flush=True)
