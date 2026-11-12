from pathlib import Path
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json,os,signal,sqlite3,time,urllib.request,uuid

r=Path('/home/toan/for_cat/evidence/schedule_oled_20261108')
dbpath=Path('/home/toan/for_cat/jetson/data/events.db')
base='http://127.0.0.1:8000'
identifier='schedule_proof_20261108_'+uuid.uuid4().hex[:8]
report={'plan_id':identifier,'trace':[],'created':False,'deleted':False}

def api(path,method='GET',body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)

def save():
    (r/(identifier+'.json')).write_text(json.dumps(report,indent=2))

def latest():
    with closing(sqlite3.connect(dbpath,timeout=2)) as db:
        return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])

def check_ready(raw,allow_finished=False):
    assert raw.get('time_valid') is True,'Clock not confirmed'
    assert raw.get('host_boot_id')==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert abs(time.monotonic()*1000-raw['updated_monotonic_ms'])<2500,'Stale MCU'
    fc=raw['telemetry']['fc_live']
    allowed=('READY','MASS OK GATE?','CAT FAULT*') if allow_finished else ('READY',)
    assert fc.get('scheduled_protocol')==1 and fc.get('bench_state') in allowed,fc
    assert isinstance(fc.get('signed_g'),(int,float)) and abs(fc['signed_g'])<=2,'Empty bowl not at zero'
    assert not fc.get('dog_running'),'DOG alarm active'

def interrupted(signum,frame):raise RuntimeError('Interrupted '+str(signum))

for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,interrupted)

try:
    report['before_plans']=api('/api/meal-plans')['plans']
    check_ready(latest(),allow_finished=True)
    # Owner has explicitly confirmed the gate is physically aligned CLOSED.
    cmd=Path('/tmp/for_cat_cmd.txt');temp=Path('/tmp/forcat_schedule_align_'+str(os.getpid())+'.txt')
    with temp.open('x') as f:f.write('inspect_ok\nservo_position\n')
    try:os.link(str(temp),str(cmd))
    finally:temp.unlink()
    for _ in range(6):
        time.sleep(.5)
        if latest()['telemetry']['fc_live'].get('bench_state')=='READY':break
    check_ready(latest())
    now=datetime.now(timezone(timedelta(hours=7)))
    due=(now+timedelta(seconds=90)).replace(second=0,microsecond=0)
    plan={'plan_id':identifier,'name':'Kiem thu lich 35g',
          'local_time':due.strftime('%H:%M'),'weekdays':[due.weekday()],
          'enabled':True,'target_grams':35,'timezone':'Asia/Ho_Chi_Minh'}
    report['due_at']=due.isoformat();report['definition']=plan
    # Record ownership before POST so cleanup also covers a lost HTTP response.
    report['create_attempted']=True;save()
    report['created_plan']=api('/api/meal-plans','POST',plan);report['created']=True;save()
    print('CREATED '+identifier+' DUE '+due.isoformat(),flush=True)
    deadline=time.monotonic()+150;last_state=None;result_at=None
    while time.monotonic()<deadline:
        raw=latest();fc=raw['telemetry']['fc_live']
        occurrences=api('/api/meal-plans/worker')['recent_occurrences']
        occurrence=next((x for x in occurrences if x['plan_id']==identifier),None)
        decision=(occurrence or {}).get('decision') or {}
        delivery=decision.get('delivery_state')
        row={'at':datetime.now(timezone.utc).isoformat(),'fc_live':fc,
             'occurrence':occurrence,'time_valid':raw.get('time_valid')}
        report['trace'].append(row)
        state=(fc.get('bench_state'),delivery)
        if state!=last_state or len(report['trace'])%10==0:
            print(json.dumps({'at':row['at'],'bench':state[0],'delivery':delivery,
                              'grams':fc.get('signed_g'),'dispensed_g':fc.get('dispensed_g')}),flush=True)
            last_state=state;save()
        if datetime.now(timezone.utc).timestamp()<due.timestamp()-2:
            check_ready(raw)
        if delivery in ('WEIGHT_REACHED','FAILED','REJECTED','EXPIRED','UNCERTAIN'):
            if result_at is None:
                result_at=time.monotonic();report['decision']=decision
            if time.monotonic()-result_at>=8:
                break
        time.sleep(1)
    if result_at is None:raise TimeoutError('Scheduled test did not produce a terminal result')
    with closing(sqlite3.connect(dbpath)) as db:
        report['events']=db.execute("SELECT kind,occurred_at,body FROM esp32_events WHERE kind IN ('scheduled_ack','scheduled_result') AND body LIKE ? ORDER BY seq",('%'+occurrence['request_id']+'%',)).fetchall()
    print('RESULT '+json.dumps(report.get('decision')),flush=True)
except Exception as exc:
    report['error']=repr(exc);print('ERROR '+repr(exc),flush=True)
finally:
    if report.get('create_attempted'):
        for attempt in range(3):
            try:
                plans=api('/api/meal-plans')['plans']
                item=next((x for x in plans if x['plan_id']==identifier),None)
                if item:report['cleanup']=api('/api/meal-plans/'+identifier,'DELETE',{'expected_revision':item['revision']})
                report['deleted']=True;break
            except Exception as exc:
                report['cleanup_error']=repr(exc);time.sleep(1)
        if not report['deleted']:
            # This newly generated proof ID belongs solely to this test.
            with closing(sqlite3.connect(dbpath,timeout=5)) as db:
                db.execute('UPDATE meal_plans SET deleted=1,revision=revision+1 WHERE plan_id=? AND deleted=0',(identifier,));db.commit()
            report['deleted']=True;report['cleanup_method']='SQLITE_FALLBACK_ONLY_TEST_ID'
    report['after_plans']=api('/api/meal-plans')['plans']
    report['owner_plans_unchanged']=report.get('before_plans')==report['after_plans']
    save();print('CLEANUP '+json.dumps({'test_deleted':report['deleted'],'owner_plans_unchanged':report['owner_plans_unchanged']}),flush=True)
