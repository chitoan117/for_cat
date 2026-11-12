"""Owner explicitly requested current 0.8..1.0g baseline become zero."""
from pathlib import Path
from contextlib import closing
import importlib.util,json,sqlite3,time,math,sys
spec=importlib.util.spec_from_file_location('migration',Path(__file__).with_name('deploy_firmware.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=m.R/('owner_baseline_zero_'+str(int(time.time()))+'.json')
result={'owner_requested_current_baseline_as_zero':True,'tare_sent':False}
before=m.wait_status(lambda s:s['device']==m.UART)
fc=before['telemetry']['fc_live']
assert fc['bench_state'] in ('READY','CAT FAULT*','MASS OK GATE?','CAT DONE','DONE','EXIT0') and not fc.get('dog_running'),'Machine busy; no zero command sent'
assert fc.get('meal_phase') not in ('CAPTURE','OBSERVE'),'Meal observation active; no zero command sent'
assert isinstance(fc.get('signed_g'),(int,float)) and math.isfinite(fc['signed_g']) and abs(fc['signed_g'])<=3,'Weight differs from owner baseline; no zero command sent'
resume=fc.get('demo_exited') is False or '--resume' in sys.argv
try:
    m.queue('0')
    sent=time.monotonic()*1000
    m.wait_status(lambda s:s['updated_monotonic_ms']>sent and s['telemetry']['fc_live'].get('demo_exited') is True)
    samples=[];seen=set();end=time.monotonic()+20
    while len(samples)<6 and time.monotonic()<end:
        s=m.wait_status(lambda s:s['device']==m.UART)
        stamp=s['updated_monotonic_ms'];f=s['telemetry']['fc_live']
        assert isinstance(f.get('signed_g'),(int,float)) and math.isfinite(f['signed_g']) and abs(f['signed_g'])<=3
        if stamp not in seen:samples.append(f);seen.add(stamp)
        time.sleep(.25)
    assert len(samples)==6 and max(f['signed_g'] for f in samples)-min(f['signed_g'] for f in samples)<=.4,'No stable baseline; no zero command sent'
    result['before_g']=[f['signed_g'] for f in samples]
    with closing(sqlite3.connect(m.DB)) as db:
        old_seq=db.execute('SELECT coalesce(max(seq),0) FROM esp32_events').fetchone()[0]
    m.queue('t');result['tare_sent']=True
    deadline=time.monotonic()+12;ack=None
    while time.monotonic()<deadline:
        with closing(sqlite3.connect(m.DB)) as db:
            row=db.execute("SELECT body FROM esp32_events WHERE seq>? AND kind='hx_cal' ORDER BY seq DESC LIMIT 1",(old_seq,)).fetchone()
        if row:
            ack=json.loads(row[0]);break
        time.sleep(.25)
    assert ack and ack.get('operation')=='rezero' and ack.get('ok') is True and ack.get('saved') is True,'No fresh saved rezero acknowledgement'
    result['save_ack']=ack
    time.sleep(2)
    after=[];seen=set();end=time.monotonic()+20
    while len(after)<10 and time.monotonic()<end:
        s=m.wait_status(lambda s:s['device']==m.UART);f=s['telemetry']['fc_live']
        if s['updated_monotonic_ms'] not in seen:after.append(f);seen.add(s['updated_monotonic_ms'])
        time.sleep(.25)
    assert len(after)==10
    assert all(f['grams_per_count']==fc['grams_per_count'] for f in after),'Scale factor changed'
    assert all(abs(f['tare_counts']-ack['tare_counts'])<.001 for f in after),'Saved zero differs from telemetry'
    result.update(after_g=[f['signed_g'] for f in after],tare_counts=after[-1]['tare_counts'],grams_per_count=after[-1]['grams_per_count'])
    result['near_zero']=all(isinstance(f['signed_g'],(int,float)) and abs(f['signed_g'])<=.2 for f in after)
    assert result['near_zero'],'New baseline saved but current scale is not stable near zero'
    if resume:
        m.queue('start');sent=time.monotonic()*1000
        m.wait_status(lambda s:s['updated_monotonic_ms']>sent and s['telemetry']['fc_live'].get('demo_exited') is False)
    result['previous_mode_restored']=True
finally:
    out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True);print('Evidence: '+str(out),flush=True)
