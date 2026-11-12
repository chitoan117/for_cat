import json,time,urllib.request,subprocess
from pathlib import Path
r=Path('/home/toan/for_cat/evidence/servo_relative_20261106')
states=[]
for _ in range(3):
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:
  d=json.load(response)
 e=d.get('esp32',{})
 states.append({'connected':e.get('connected'),'stale':e.get('stale'),'last_telemetry_at':e.get('last_telemetry_at'),'bench_state':d.get('bench_state'),'physical_servo_state':d.get('safety',{}).get('servo_state'),'frames_ok':e.get('counters',{}).get('frames_ok')})
 time.sleep(1)
units=['for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service']
p=subprocess.run(['systemctl','--user','is-active',*units],capture_output=True,text=True)
result={'services':dict(zip(units,p.stdout.splitlines())),'samples':states,'physical_movement_tested':False,'owner_closed_alignment_pending':True}
(r/'post_flash_status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert p.returncode==0
assert states[-1]['connected'] is True and states[-1]['stale'] is False
assert states[-1]['last_telemetry_at']!=states[0]['last_telemetry_at']
