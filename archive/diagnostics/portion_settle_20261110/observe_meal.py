from pathlib import Path
import json,time,urllib.request,sqlite3
r=Path(__file__).parent
def read():
 with urllib.request.urlopen('http://127.0.0.1:8000/api/meal-observation',timeout=2) as f:return json.load(f)
data=read();first=data.get('live') or {};meal_id=first.get('meal_id');assert meal_id,'No measured meal'
out=r/('meal_'+meal_id+'.json');result={'meal_id':meal_id,'first_live':first,'samples':[]}
deadline=time.monotonic()+130;previous=None;last_print=0
while time.monotonic()<deadline:
 data=read();v=data.get('live') or {}
 if v.get('meal_id')!=meal_id:result['outcome']='NEXT_CYCLE_ALREADY_STARTED';break
 entry={k:v.get(k) for k in ('meal_phase','meal_food','meal_starting_g','meal_remaining_g','meal_consumed_g','meal_preference','meal_elapsed_seconds','meal_stable','signed_g')}
 result['samples'].append(entry)
 if entry['meal_phase']!=previous or time.monotonic()-last_print>=25:
  print(json.dumps(entry),flush=True);previous=entry['meal_phase'];last_print=time.monotonic()
 records=[m for m in data.get('records',[]) if m.get('meal_id')==meal_id]
 if records:result['outcome']='FINAL_MEASURED_RECORD_SAVED';result['record']=records[0];break
 if v.get('meal_phase')=='INVALID':result['outcome']='INVALID_MEASUREMENT';break
 time.sleep(1)
else:result['outcome']='STILL_OBSERVING'
with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db') as db:
 result['portion_checks']=[{'timestamp':at,'body':json.loads(body)} for at,body in db.execute("SELECT occurred_at,body FROM esp32_events WHERE kind='portion_check' ORDER BY seq DESC LIMIT 3")]
result['final_live']=data.get('live');out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('first_live','samples','final_live')},indent=2),flush=True)
print('Evidence: '+str(out),flush=True)
