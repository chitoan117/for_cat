from pathlib import Path
import sqlite3,json,urllib.request
with sqlite3.connect('file:/home/toan/for_cat/jetson/data/events.db?mode=ro',uri=True) as db:
 out={}
 for table in ['meal_plans','scheduled_occurrences','feed_dry_run_requests']:
  out[table+'_count']=db.execute('SELECT count(*) FROM '+table).fetchone()[0]
  cur=db.execute('SELECT * FROM '+table+' ORDER BY rowid DESC LIMIT 8');out[table]=[dict(zip([d[0] for d in cur.description],r)) for r in cur.fetchall()]
 print(json.dumps(out,indent=2))
for path in ['/api/meal-plans','/api/meal-plans/worker']:
 with urllib.request.urlopen('http://127.0.0.1:8000'+path) as res:print(path,res.read().decode())
