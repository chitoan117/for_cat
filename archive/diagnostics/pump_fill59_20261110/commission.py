from pathlib import Path
import os,time,re,json,sqlite3

r=Path('/home/toan/for_cat/evidence/pump_fill59_20261110')
def send(body):
    p=Path('/tmp/fc_fill59_'+str(os.getpid())+'.txt')
    with p.open('x') as f:f.write(body+'\n')
    try:os.link(str(p),'/tmp/for_cat_cmd.txt')
    finally:p.unlink()
def telemetry():
    with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db') as db:
        return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
def log():
    with open('/var/log/syslog','rb') as f:f.seek(offset);return f.read().decode('utf8','replace')
result={'on_commands_sent':0,'stop_cm':5.9,'native_max_ms':10000,
        'physical_water_flow_after_off':'AWAITING_OWNER_OBSERVATION'}
try:
    send('0\npump_driver_verified\npump_status\nmode')
    time.sleep(3)
    v=telemetry()
    assert abs(time.monotonic()*1000-v['updated_monotonic_ms'])<2500,'Telemetry not fresh'
    fc=v['telemetry']['fc_live']
    assert abs(fc['tare_counts']-(-699593.0))<.001,'Tare changed from owner-confirmed zero 2026-11-10'
    assert abs(fc['grams_per_count']-(-.000945082600219258))<1e-12,'Scale factor changed'
    assert 'servo_moving=0' in log(),'Servo not idle'
    result['scale_before']={k:fc[k] for k in ('tare_counts','grams_per_count','signed_g')}
    send('pump_fill59')
    result['on_commands_sent']=1
    deadline=time.monotonic()+14
    while time.monotonic()<deadline:
        txt=log()
        if any(x in txt for x in ('PUMP FILL59 DONE:','PUMP FILL59 NO START:','PUMP FILL59 BLOCKED:')):break
        time.sleep(.3)
    result['start_ack']='PUMP FILL59 START:' in log()
    result['target_ack']='PUMP FILL59 DONE: TARGET_59CM' in log()
    result['completion']=next((s for s in log().splitlines() if any(x in s for x in ('PUMP FILL59 DONE:','PUMP FILL59 NO START:','PUMP FILL59 BLOCKED:'))),None)
finally:
    send('pump_off\npump_off\npump_status')
    time.sleep(2)
    result['off_ack']='PUMP OFF GPIO7 LOW.' in log()
    result['log']=[s for s in log().splitlines() if '[esp32]' in s]
    (r/'commission_result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
