from pathlib import Path
import json,sqlite3,time,urllib.request
R=Path(__file__).resolve().parent
assert not Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00').exists(),'USB still connected'
before=json.loads((R/'preflight.json').read_text())['telemetry']['fc_live']
frames=[];seen=set();end=time.monotonic()+12
while len(frames)<8 and time.monotonic()<end:
    with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db',timeout=2) as db:
        s=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    stamp=s['updated_monotonic_ms'];fc=s['telemetry']['fc_live']
    assert 0<=time.monotonic()*1000-stamp<2500 and s['device']=='/dev/ttyTHS1'
    assert fc['pump_auto_enabled'] is False and fc['pump_auto_running'] is False
    assert abs(fc['pump_on_cm']-5.7)<.001 and abs(fc['pump_off_cm']-5.5)<.001 and fc['pump_max_run_ms']==10000
    for k in ('tare_counts','grams_per_count','backup_enabled'):assert fc[k]==before[k],k
    assert fc['demo_exited'] is False
    if stamp not in seen:
        seen.add(stamp);frames.append({'stamp':stamp,'boot':s.get('boot'),'d1':s['telemetry']['ultrasonic']['JSN_SR04T_1'],'water_enabled':fc['pump_auto_enabled'],'water_running':fc['pump_auto_running']})
    time.sleep(.2)
assert len(frames)>=8,'Not enough distinct fresh UART updates'
with urllib.request.urlopen('http://127.0.0.1:8000/api/water-control',timeout=4) as response:water=json.load(response)
assert water['fresh'] and water['policy_ready'] and water['enabled'] is False and water['running'] is False
assert water['request']['action']=='DISABLE' and water['request']['status']=='APPLIED'
result={'usb_absent':True,'uart':'/dev/ttyTHS1','distinct_fresh_frames':len(frames),'water':water,'calibration_preserved':True,'backup_preserved':True,'normal_feed_mode_restored':True,'pump_enable_sent':False,'physical_flow_test':False,'frames':frames}
(R/'external_result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='frames'}))
