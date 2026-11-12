"""Owner confirmed empty stationary bowl; preserve gain and save the new zero in ESP NVS."""
from pathlib import Path
import json,math,os,sqlite3,time,urllib.request,statistics
R=Path(__file__).resolve().parent;DB=Path('/home/toan/for_cat/jetson/data/events.db')
OUT=R/('zero_'+str(int(time.time()))+'.json')
result={'owner_confirmed_empty_stationary_bowl':True,'tare_sent':False}
def fresh(timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        with sqlite3.connect(DB,timeout=2) as db:s=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        if s['device']=='/dev/ttyTHS1' and 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500:return s
        time.sleep(.2)
    raise RuntimeError('No fresh UART scale state')
def queue(commands):
    p=Path('/tmp/for_cat_cmd.txt');end=time.monotonic()+8
    while p.exists() and time.monotonic()<end:time.sleep(.1)
    assert not p.exists(),'Command inbox occupied; no overwrite'
    temp=Path('/tmp/forcat_zero_%s.txt'%os.getpid());temp.write_text(commands+'\n')
    try:os.link(temp,p)
    finally:temp.unlink()
def wait_mode(exited):
    end=time.monotonic()+8
    while time.monotonic()<end:
        s=fresh(3)
        if s['telemetry']['fc_live'].get('demo_exited') is exited:return s
        time.sleep(.2)
    raise RuntimeError('Mode acknowledgement unavailable')
before=fresh();fc=before['telemetry']['fc_live'];result['before']=fc
assert fc['bench_state'] in ('READY','CAT FAULT*','CAT DONE','DONE','EXIT0') and not fc.get('dog_running'),'Device busy; no zero sent'
assert fc.get('meal_phase') not in ('CAPTURE','OBSERVE','CAPTURING','OBSERVING'),'Active meal; no zero sent'
assert type(fc.get('signed_g')) in (int,float) and math.isfinite(fc['signed_g']) and abs(fc['signed_g'])<=5,'Weight does not match small empty-bowl drift'
assert fc.get('pump_auto_enabled') is False and fc.get('pump_auto_running') is False,'Pump must be off while taking zero'
resume=fc.get('demo_exited') is False;paused=False
try:
    queue('0');wait_mode(True);paused=True
    samples=[];seen=set();end=time.monotonic()+25
    while time.monotonic()<end:
        s=fresh(3);f=s['telemetry']['fc_live'];g=f.get('signed_g')
        assert type(g) in (int,float) and math.isfinite(g) and abs(g)<=5
        if s['updated_monotonic_ms'] not in seen:
            seen.add(s['updated_monotonic_ms']);samples.append(g)
        if len(samples)>=8 and max(samples[-8:])-min(samples[-8:])<=.4:break
        time.sleep(.2)
    assert len(samples)>=8 and max(samples[-8:])-min(samples[-8:])<=.4,'Scale not stable; no tare command sent'
    result['before_samples_g']=samples
    with sqlite3.connect(DB,timeout=2) as db:old_seq=db.execute('SELECT coalesce(max(seq),0) FROM esp32_events').fetchone()[0]
    queue('t');result['tare_sent']=True
    ack=None;end=time.monotonic()+14
    while time.monotonic()<end:
        with sqlite3.connect(DB,timeout=2) as db:rows=db.execute("SELECT body FROM esp32_events WHERE seq>? AND kind='hx_cal' ORDER BY seq DESC LIMIT 5",(old_seq,)).fetchall()
        for row in rows:
            value=json.loads(row[0])
            if value.get('operation')=='rezero':ack=value;break
        if ack:break
        time.sleep(.2)
    result['save_ack']=ack
    assert ack and ack.get('ok') is True and ack.get('saved') is True,'No fresh NVS save acknowledgement'
    time.sleep(2)
    after=[];seen=set();end=time.monotonic()+18
    while len(after)<10 and time.monotonic()<end:
        s=fresh(3);f=s['telemetry']['fc_live']
        assert f['grams_per_count']==fc['grams_per_count'],'Gain changed'
        assert abs(f['tare_counts']-ack['tare_counts'])<.001,'Telemetry zero does not match saved acknowledgement'
        if s['updated_monotonic_ms'] not in seen:
            seen.add(s['updated_monotonic_ms']);after.append(f)
        time.sleep(.2)
    assert len(after)==10
    result.update(after_samples_g=[f['signed_g'] for f in after],display_samples_g=[f['grams'] for f in after],tare_counts=after[-1]['tare_counts'],grams_per_count=after[-1]['grams_per_count'])
    result['near_zero']=all(abs(f['signed_g'])<=.3 for f in after)
    result['display_zero_latest']=abs(after[-1]['grams'])<.05
    result['after_mean_g']=statistics.mean(result['after_samples_g'])
    with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=4) as r:state=json.load(r)
    result['web_weight']=state.get('weight');result['web_grams']=state.get('grams')
    result['success']=True
finally:
    if paused and resume:
        try:queue('start');wait_mode(False);result['normal_mode_restored']=True
        except Exception as exc:result['normal_mode_restored']=False;result['resume_error']=str(exc)
    OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('before','web_weight')},indent=2),flush=True);print('Evidence: '+str(OUT),flush=True)
