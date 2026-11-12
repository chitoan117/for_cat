from pathlib import Path
import json,os,sqlite3,time,urllib.request,subprocess
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson');USB=Path('/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00');UART='/dev/ttyTHS1'
assert not USB.exists(),'USB still connected; external UART-only test is not valid'
baseline=json.loads((R/'boot_uart_frame.json').read_text())
def snapshot():
    with sqlite3.connect(ROOT/'data/events.db',timeout=2) as db:return json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
def fresh(timeout=18):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        s=snapshot()
        if s['device']==UART and 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500:return s
        time.sleep(.2)
    raise RuntimeError('No fresh UART data after USB removal')
def queue(commands):
    inbox=Path('/tmp/for_cat_cmd.txt');end=time.monotonic()+8
    while inbox.exists() and time.monotonic()<end:time.sleep(.15)
    assert not inbox.exists(),'Command inbox occupied'
    temp=Path('/tmp/uart_verify_%s.txt'%os.getpid());temp.write_text(commands+'\n')
    try:os.link(temp,inbox)
    finally:temp.unlink()
pre=fresh();fc=pre['telemetry']['fc_live']
if fc.get('demo_exited') is True:
    assert fc.get('bench_state') in ('READY','EXIT0','DONE','CAT DONE','CAT FAULT*') and fc.get('meal_phase') not in ('CAPTURING','OBSERVING')
    queue('start\nmode\npump_status')
samples=[];seen=set();end=time.monotonic()+45
while time.monotonic()<end:
    assert not USB.exists(),'USB appeared during UART-only observation'
    s=fresh(3);fc=s['telemetry']['fc_live'];stamp=s['updated_monotonic_ms'];uptime=s['telemetry']['monotonic_ms']
    for key in ('tare_counts','grams_per_count'):assert abs(fc[key]-baseline[key])<1e-8,key
    assert fc['pump_auto_enabled'] is False and fc['pump_auto_running'] is False
    assert fc['backup_enabled'] is True and fc['demo_exited'] is False
    assert abs(fc['pump_on_cm']-5.7)<.001 and abs(fc['pump_off_cm']-5.5)<.001
    if stamp not in seen:
        seen.add(stamp);samples.append({'stamp':stamp,'device_ms':uptime,'backup_offline':fc['backup_offline'],'counters':s['counters']})
    if len(samples)>=20 and uptime>=32000:break
    time.sleep(.2)
assert len(samples)>=20 and samples[-1]['device_ms']>=32000
assert all(b['device_ms']>a['device_ms'] for a,b in zip(samples,samples[1:])),'ESP rebooted during observation'
assert all(x['backup_offline'] is False for x in samples if x['device_ms']>=30000),'ESP is not receiving host heartbeats'
assert samples[-1]['counters']['reconnects']==samples[0]['counters']['reconnects'],'Bridge reconnected'
assert samples[-1]['counters']['frames_bad']==samples[0]['counters']['frames_bad'],'Malformed frame received'
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:state=json.load(response)
assert state['esp32']['connected'] is True and 'reservoirs' in state
for unit in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service'):
    subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True)
result={'usb_absent':True,'port':UART,'distinct_fresh_frames':len(samples),'esp_uptime_end_ms':samples[-1]['device_ms'],'no_reboot':True,'reconnects_during_observation':0,'new_bad_frames':0,'host_to_esp_heartbeat_confirmed_after_boot_grace':True,'calibration_preserved':True,'normal_feed_mode_restored':True,'backup_enabled':True,'water_enabled':False,'source_sensor_readings':{k:v['distance_cm'] for k,v in state['ultrasonic'].items()},'signed_scale_g':fc.get('signed_g'),'reservoirs':state['reservoirs'],'actuator_test_sent':False,'samples':samples}
(R/'external_result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='samples'}))
