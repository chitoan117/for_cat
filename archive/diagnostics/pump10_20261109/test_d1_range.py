from pathlib import Path
from contextlib import closing
import sqlite3,json,os,time,math
root=Path('/home/toan/for_cat/evidence/pump10_20261109')
dbpath='/home/toan/for_cat/jetson/data/events.db'
def send(command):
    p=Path('/tmp/fc_d1_range_'+str(os.getpid())+'.txt')
    with p.open('x') as f:f.write(command+'\n')
    try:os.link(str(p),'/tmp/for_cat_cmd.txt')
    finally:p.unlink()
def sample():
    with closing(sqlite3.connect(dbpath)) as db:
        row=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    fresh=abs(time.monotonic()*1000-row['updated_monotonic_ms'])<2500
    d1=row['telemetry']['ultrasonic']['JSN_SR04T_1'] # Legacy key; physical D1 is GPIO14/15 HC-SR04.
    cm=d1.get('distance_cm')
    ok=fresh and d1.get('valid') is True and not d1.get('timeout') and isinstance(cm,(int,float)) and math.isfinite(cm)
    return row['last_received_at'],ok,cm,row['host_boot_id']
send('pump_off\n0')
time.sleep(3)
stamp,ok,cm,boot=sample()
deadline=time.monotonic()+75
last=None;hits=0;started=None;triggered=False;observed=[];last_print=None
try:
    while time.monotonic()<deadline:
        stamp,ok,cm,current_boot=sample()
        assert current_boot==boot,'Jetson rebooted; test cancelled'
        in_range=ok and 10<=cm<=20
        if stamp!=last:
            observed.append({'stamp':stamp,'valid':ok,'cm':cm})
            hits=hits+1 if in_range else 0
            last=stamp
            status=(ok,round(cm,1) if isinstance(cm,(int,float)) else cm)
            if status!=last_print:
                print(json.dumps({'D1_valid':ok,'D1_cm':cm,'confirmations':hits}),flush=True)
                last_print=status
        if not triggered and hits>=2:
            send('pump_test')
            started=time.monotonic();triggered=True
            print('PUMP_TEST_SENT_ONCE: D1 has two fresh readings10..20cm; firmware limit10s.',flush=True)
        if triggered and (not in_range or time.monotonic()-started>=10.5):
            print('STOP: '+('D1 left range or lost signal' if not in_range else 'Test duration reached'),flush=True)
            break
        time.sleep(.2)
finally:
    send('pump_off')
    result={'test':'D1_10_TO_20_CM','triggered_once':triggered,'max_duration_ms':10000,
            'calibration_saved':False,'persistent_auto_enabled':False,'samples':observed}
    out=root/('d1_range_'+str(int(time.time()))+'.json')
    out.write_text(json.dumps(result,indent=2))
    print(json.dumps({'triggered_once':triggered,'evidence':str(out),'pump_off_sent':True}),flush=True)
