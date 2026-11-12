from pathlib import Path
from datetime import datetime,timedelta,timezone
import json,urllib.request

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
base='http://127.0.0.1:8000'
identifier='plan_50281fb2793d369478eb012b42db0169'
def api(path,method='GET',body=None):
    req=urllib.request.Request(base+path,method=method,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5) as resp:return json.load(resp)
now=datetime.now(timezone(timedelta(hours=7)))
due=now.replace(hour=12,minute=35,second=0,microsecond=0)
assert now.date().isoformat()=='2026-11-08' and due.timestamp()-now.timestamp()>20,'Requested time has passed or too little time remains'
all_plans=api('/api/meal-plans')
plan=next(x for x in all_plans['plans'] if x['plan_id']==identifier)
assert plan['revision']==2 and plan['local_time']=='12:25','Owner changed plan; reload before editing'
body={key:plan[key] for key in ('name','local_time','weekdays','enabled','target_grams','timezone')}
body.update(local_time='12:35',target_grams=35,expected_revision=plan['revision'])
report={'before':plan,'request':body,'requested_due_at':due.isoformat()}
(r/'schedule_1235_update.json').write_text(json.dumps(report,indent=2))
report['after']=api('/api/meal-plans/'+identifier,'PUT',body)
assert report['after']['local_time']=='12:35' and report['after']['target_grams']==35
(r/'schedule_1235_update.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
