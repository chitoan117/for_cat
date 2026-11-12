from pathlib import Path
from collections import deque
from contextlib import closing
import os,time,json,sqlite3

root=Path('/home/toan/for_cat/evidence/pump_fill59_20261110')
out=root/('owner_rezero_'+str(int(time.time()))+'.json')
result={'owner_confirmed_empty_bowl':True,'tare_sent':False}
def send(body):
    p=Path('/tmp/fc_owner_zero_'+str(os.getpid())+'.txt')
    with p.open('x') as f:f.write(body+'\n')
    try:os.link(str(p),'/tmp/for_cat_cmd.txt')
    finally:p.unlink()
def sample():
    with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db')) as db:
        r=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert abs(time.monotonic()*1000-r['updated_monotonic_ms'])<2500,'Telemetry stale'
    f=r['telemetry']['fc_live']
    assert f['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?') and not f.get('dog_running'),'Scale busy'
    assert isinstance(f.get('signed_g'),(int,float)) and abs(f['signed_g'])<1000,'Invalid weight'
    return r['updated_monotonic_ms'],f
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
try:
    send('pump_auto off\npump_off\n0')
    time.sleep(2)
    w=deque(maxlen=8);last=None;deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        stamp,f=sample()
        if stamp!=last:
            w.append(f);last=stamp
            if len(w)==8 and max(x['signed_g'] for x in w)-min(x['signed_g'] for x in w)<=.4:break
        time.sleep(.5)
    else:raise AssertionError('No stable empty-bowl window; no tare sent')
    result['before']=list(w)
    print(json.dumps({'before_g':[x['signed_g'] for x in w],'stable':True}),flush=True)
    send('t')
    result['tare_sent']=True
    time.sleep(4)
    after=[];last=None;deadline=time.monotonic()+18
    while len(after)<12 and time.monotonic()<deadline:
        stamp,f=sample()
        if stamp!=last:after.append(f);last=stamp
        time.sleep(.5)
    result['after']=after
    assert len(after)>=10,'Insufficient fresh verification samples'
    assert all(x['grams_per_count']==w[0]['grams_per_count'] for x in after),'Calibration factor changed'
    with open('/var/log/syslog','rb') as f:f.seek(offset);log=f.read().decode('utf8','replace')
    result['log']=[s for s in log.splitlines() if '[esp32]' in s]
    v=[x['signed_g'] for x in after]
    result.update(after_g=v,min_g=min(v),max_g=max(v),tare_counts=after[-1]['tare_counts'],factor=after[-1]['grams_per_count'])
    result['save_ack']=any('"operation":"rezero"' in s and '"saved":true' in s for s in result['log'])
    result['near_zero']=all(abs(x)<=.2 for x in v)
finally:
    out.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('before','after','log')},indent=2),flush=True)
    print('Evidence: '+str(out),flush=True)
