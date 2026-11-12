from pathlib import Path
import json,os,sqlite3,time,urllib.request,subprocess
R=Path(__file__).resolve().parent;ROOT=Path('/home/toan/for_cat/jetson');PORT='/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00'
baseline=json.loads((R/'boot_usb_frame.json').read_text())
inbox=Path('/tmp/for_cat_cmd.txt');end=time.monotonic()+8
while inbox.exists() and time.monotonic()<end:time.sleep(.15)
assert not inbox.exists();temp=Path('/tmp/usb_resume_%s.txt'%os.getpid());temp.write_text('start\nmode\npump_status\n')
try:os.link(temp,inbox)
finally:temp.unlink()
samples=[];seen=set();end=time.monotonic()+24
while len(samples)<16 and time.monotonic()<end:
    with sqlite3.connect(ROOT/'data/events.db',timeout=2) as db:s=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    assert 0<=time.monotonic()*1000-s['updated_monotonic_ms']<2500 and s['device']==PORT
    fc=s['telemetry']['fc_live']
    for k in ('tare_counts','grams_per_count'):assert fc[k]==baseline[k]
    assert fc['pump_auto_enabled'] is False and fc['pump_auto_running'] is False and fc['backup_enabled'] is True
    assert s['counters']['reconnects']==0 and s['counters']['frames_bad']==0
    if fc['demo_exited'] is False and s['updated_monotonic_ms'] not in seen:
        seen.add(s['updated_monotonic_ms']);samples.append({'stamp':s['updated_monotonic_ms'],'device_ms':s['telemetry']['monotonic_ms'],'counters':s['counters']})
    time.sleep(.2)
assert len(samples)>=16
assert all(b['device_ms']>a['device_ms'] for a,b in zip(samples,samples[1:]))
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=4) as r:state=json.load(r)
assert state['esp32']['connected'] is True
for role in ('food','water'):
    view=state['reservoirs'][role]
    assert view['calibration']=='EMPTY_ONLY' and view['full_cm'] is None
    if not view['valid']:assert view['percent'] is None
for unit in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service'):
    subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True)
result={'usb_communication_verified':True,'distinct_fresh_frames':len(samples),'reconnects':0,'bad_frames':0,'normal_feed_mode_restored':True,'backup_enabled':True,'water_auto_enabled':False,'calibration_preserved':True,'reservoirs':state['reservoirs'],'owner_deferred_sensor_power':True,'physical_sensor_and_pump_test_pending':True,'samples':samples}
(R/'runtime_result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='samples'}))
