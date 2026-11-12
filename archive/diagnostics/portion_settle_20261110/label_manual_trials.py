from pathlib import Path
from datetime import datetime,timezone
import json,sqlite3,sys,time
r=Path(__file__).parent
def mark(meal_id):
 with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db',timeout=2) as db:
  db.execute('BEGIN IMMEDIATE')
  rows=db.execute("SELECT seq,body FROM esp32_events WHERE kind='meal_preference' ORDER BY seq DESC LIMIT 200").fetchall()
  match=[(seq,body,json.loads(body)) for seq,body in rows if json.loads(body).get('meal_id')==meal_id]
  assert len(match)==1,'Expected one final measured record: '+meal_id
  seq,body,m=match[0]
  if m.get('observation_mode')=='MANUAL_TEST':return {'meal_id':meal_id,'already_annotated':True}
  original=r/('raw_'+meal_id+'_before_manual_note.json');assert not original.exists()
  original.write_text(body,encoding='utf8')
  m.update(observation_mode='MANUAL_TEST',behavior_validated=False,owner_confirmed_manual_removal=True,
   owner_note='User confirmed removing food by hand to test the algorithm; this is not evidence of real cat eating.')
  m['original_conclusion']=m.get('conclusion')
  m['conclusion']='KIEM THU BANG TAY: '+m['food']+' -> '+m['classification']
  changed=db.execute('UPDATE esp32_events SET body=? WHERE seq=? AND body=?',(json.dumps(m,separators=(',',':')),seq,body))
  assert changed.rowcount==1
  at=datetime.now(timezone.utc).isoformat()
  db.execute('INSERT INTO esp32_events(kind,occurred_at,body) VALUES(?,?,?)',('meal_test_annotation',at,json.dumps({'meal_id':meal_id,'event_seq':seq,'observation_mode':'MANUAL_TEST','owner_confirmed':True})))
  db.commit()
 return {'meal_id':meal_id,'event_seq':seq,'observation_mode':'MANUAL_TEST','classification':m['classification'],
  'starting_g':m['starting_g'],'remaining_g':m['remaining_g'],'consumed_g':m['consumed_g'],'raw_measurements_preserved':True}
if __name__=='__main__':
 results=[mark(x) for x in sys.argv[1:]]
 (r/('manual_labels_'+str(int(time.time()))+'.json')).write_text(json.dumps(results,indent=2),encoding='utf8')
 print(json.dumps(results,indent=2),flush=True)
