from pathlib import Path
import json,time,urllib.request,os
r=Path('/home/toan/for_cat/evidence/cat_gate_check_20261106');r.mkdir(exist_ok=True)
rows=[]
for _ in range(20):
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:d=json.load(response)
 rows.append({'time':d.get('observed_at'),'ai':d.get('ai'),'e1_cm':d.get('approach',{}).get('distance_cm'),
   'e1_valid':d.get('approach',{}).get('valid'),'grams':d.get('grams'),'state':d.get('bench_state'),
   'cat_requests':d.get('esp32',{}).get('counters',{}).get('cat_triggers')})
 time.sleep(1)
(r/'observations.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
