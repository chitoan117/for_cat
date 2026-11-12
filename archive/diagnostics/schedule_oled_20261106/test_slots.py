from contextlib import closing
from datetime import timedelta
import sqlite3,json
from app.meal_plans import MealPlans,UpdatePlan
from app.scheduled_worker import ScheduledOccurrences
from test_scheduled_worker import NOW,safe,plan,worker,rows

def test_retime_same_day_creates_new_slot_rename_and_restart_do_not(tmp_path):
 path=tmp_path/'slots.db';p=plan(path);w=worker(path);first=w.tick()[0]
 values={k:p[k] for k in ('name','local_time','weekdays','enabled','target_grams','timezone')}
 MealPlans(path).update(p['plan_id'],UpdatePlan(**{**values,'local_time':'09:31'},expected_revision=1))
 second=w.tick(now=NOW+timedelta(minutes=1))[0]
 assert second['occurrence_id']!=first['occurrence_id'] and rows(path,'scheduled_occurrences')==2
 MealPlans(path).update(p['plan_id'],UpdatePlan(**{**values,'local_time':'09:31','name':'renamed'},expected_revision=2))
 assert worker(path).tick(now=NOW+timedelta(minutes=1))[0]['occurrence_state']=='ALREADY_SUBMITTED'
 assert rows(path,'feed_dry_run_requests')==2

def test_existing_daily_ledger_migrates_without_replaying_old_slot(tmp_path):
 path=tmp_path/'legacy.db';p=plan(path);due=int((NOW-timedelta(seconds=10)).timestamp()*1000)
 with closing(sqlite3.connect(path)) as db:
  db.execute('CREATE TABLE scheduled_occurrences(occurrence_id TEXT PRIMARY KEY,plan_id TEXT,local_date TEXT,due_unix_ms INTEGER,plan_revision INTEGER,request_id TEXT UNIQUE,created_at TEXT,origin TEXT,UNIQUE(plan_id,local_date))')
  db.execute('CREATE TABLE feed_dry_run_requests(request_id TEXT PRIMARY KEY,body TEXT,decision TEXT)')
  body={'request_id':'legacy','source':'SCHEDULED','target_grams':35,'actuator_execution':False,'actual_dispensed_grams':None}
  db.execute('INSERT INTO feed_dry_run_requests VALUES(?,?,NULL)',('legacy',json.dumps(body)))
  db.execute('INSERT INTO scheduled_occurrences VALUES(?,?,?,?,?,?,?,?)',('old',p['plan_id'],'2026-10-26',due,1,'legacy',NOW.isoformat(),'WORKER'));db.commit()
 store=ScheduledOccurrences(path);result=store.submit(p['plan_id'],safe(),NOW,origin='WORKER')
 assert result['occurrence_state']=='ALREADY_SUBMITTED' and result['request']['request']['request_id']=='legacy' and result['occurrence_id']=='old'
 assert rows(path,'scheduled_occurrences')==1
