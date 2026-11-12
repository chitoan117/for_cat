from pathlib import Path
from contextlib import closing
import sqlite3,json,os,time,math
root=Path('/home/toan/for_cat/evidence/pump10_20261109')
def send(body):
    p=Path('/tmp/fc_d1_15cm_'+str(os.getpid())+'.txt')
    with p.open('x') as f:f.write(body+'\n')
    try:os.link(str(p),'/tmp/for_cat_cmd.txt')
    finally:p.unlink()
def sample():
    with closing(sqlite3.connect('/home/toan/for_cat/jetson/data/events.db')) as db:
        row=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    fresh=abs(time.monotonic()*1000-row['updated_monotonic_ms'])<2500
    d=row['telemetry']['ultrasonic']['JSN_SR04T_1']
    cm=d.get('distance_cm')
    valid=fresh and d.get('valid') is True and not d.get('timeout') and isinstance(cm,(float,int)) and math.isfinite(cm)
    return {'stamp':row['last_received_at'],'valid':valid,'cm':cm,'boot':row['host_boot_id'],'mcu_ms':row['telemetry']['monotonic_ms']}
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
send('pump_off\n0');time.sleep(3)
initial=sample();boot=initial['boot'];last_mcu=initial['mcu_ms']
deadline=time.monotonic()+75
started=None;last=None;hits=0;observed=[];last_print=None;reason='NO_D1_15CM_TRIGGER'
try:
    while started is not None or time.monotonic()<deadline:
        s=sample()
        if s['boot']!=boot or s['mcu_ms']<last_mcu:
            reason='DEVICE_RESTART';break
        last_mcu=s['mcu_ms']
        if s['stamp']!=last:
            hits=hits+1 if s['valid'] and 14<=s['cm']<=16 else 0
            last=s['stamp'];observed.append(s)
            key=(s['valid'],round(s['cm'],1) if s['cm'] is not None else None)
            if key!=last_print:
                print(json.dumps({'D1_valid':s['valid'],'D1_cm':s['cm'],'confirmations':hits}),flush=True);last_print=key
        if started is None and hits>=2:
            send('pump_test');started=time.monotonic()
            print('ONE_PUMP_TEST_SENT: D1 stable14..16cm;10s maximum.',flush=True)
        if started is not None:
            if not s['valid']:reason='D1_SIGNAL_LOST';break
            if time.monotonic()-started>=10.5:reason='TEST_DURATION_REACHED';break
        time.sleep(.2)
finally:
    send('pump_off');time.sleep(3)
    with open('/var/log/syslog','rb') as f:f.seek(offset);log=f.read().decode('utf-8','replace')
    lines=[x for x in log.splitlines() if '[esp32]' in x]
    result={'test':'D1_15CM_TOLERANCE_1CM','test_sent_once':started is not None,'reason':reason,
            'start_ack':any('PUMP TEST START:' in x for x in lines),
            'timer_stop_ack':any('PUMP TEST DONE:' in x for x in lines),
            'off_ack':any('PUMP OFF GPIO7 LOW.' in x for x in lines[-8:]),
            'pump_log':[x for x in lines if 'PUMP' in x or 'rst:' in x],
            'samples':observed,'physical_flow':'AWAITING_OWNER','persistent_auto_enabled':False}
    out=root/('d1_15cm_'+str(int(time.time()))+'.json');out.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}),flush=True)
    print('EVIDENCE '+str(out),flush=True)
