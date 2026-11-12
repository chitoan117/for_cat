"""Verify UART without ESP32 USB, then restore the previously enabled mode."""
from pathlib import Path
import importlib.util,json,subprocess,time,urllib.request
spec=importlib.util.spec_from_file_location('deployment',Path(__file__).with_name('deploy_uart.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert not m.USB.exists(),'USB is still present; external-only power test not valid'
before=m.wait_status(lambda s:s['device']==m.UART)
m.queue('0\nservo_position\nmode\nhx_diag')
sent=time.monotonic()*1000
paused=m.wait_status(lambda s:s['device']==m.UART and s['updated_monotonic_ms']>sent and s['telemetry']['fc_live'].get('demo_exited') is True)
baseline=json.loads((m.R/'preflight.json').read_text())['telemetry']['fc_live']
m.check_calibration(baseline,paused['telemetry']['fc_live'])
first=paused;last=paused;stamps=set();end=time.monotonic()+20
while time.monotonic()<end:
    assert not m.USB.exists(),'USB reappeared during external-only test'
    last=m.wait_status(lambda s:s['device']==m.UART,timeout=3)
    stamps.add(last['updated_monotonic_ms'])
    assert last['telemetry']['fc_live'].get('demo_exited') is True
    assert last['counters']['reconnects']==first['counters']['reconnects']
    time.sleep(.35)
assert len(stamps)>=10,'Insufficient distinct external-only UART frames'
assert last['telemetry']['monotonic_ms']>first['telemetry']['monotonic_ms']
assert last['telemetry']['sensors']['hx711']['raw_available'],'Scale not reporting under external power'
m.check_calibration(baseline,last['telemetry']['fc_live'])
m.queue('start\nservo_position\nmode')
sent=time.monotonic()*1000
resumed=m.wait_status(lambda s:s['device']==m.UART and s['updated_monotonic_ms']>sent and s['telemetry']['fc_live'].get('demo_exited') is False)
with urllib.request.urlopen('http://127.0.0.1:8000/app',timeout=5) as response:
    assert response.status==200
for unit in ('for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service'):
    subprocess.run(['systemctl','--user','is-active','--quiet',unit],check=True)
result={'usb_removed':True,'uart_port':m.UART,'distinct_frames_20_seconds':len(stamps),'reconnects_during_observation':0,'calibration_unchanged':True,'bidirectional_pause_and_resume_verified':True,'normal_mode_restored':True,'web_http_status':200,'explicit_servo_or_pump_test_sent':False,'live':resumed}
(m.R/'external_power_result.json').write_text(json.dumps(result,indent=2))
summary={k:v for k,v in result.items() if k!='live'}
summary['scale_g']=resumed['telemetry']['fc_live']['signed_g']
summary['sensor_distances_cm']={k:v['distance_cm'] for k,v in resumed['telemetry']['ultrasonic'].items()}
print(json.dumps(summary),flush=True)
