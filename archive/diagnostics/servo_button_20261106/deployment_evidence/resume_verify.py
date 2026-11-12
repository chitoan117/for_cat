from pathlib import Path
import os,time,json,urllib.request,subprocess
r=Path('/home/toan/for_cat/evidence/servo_button_20261106')
cmd=Path('/tmp/for_cat_cmd.txt')
deadline=time.monotonic()+5
while cmd.exists() and time.monotonic()<deadline:time.sleep(0.1)
assert not cmd.exists(),'Do not overwrite another pending command'
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/for_cat_resume_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('start\nservo_position\nmode\n')
 os.link(tmp,cmd)
finally:
 if tmp.exists():tmp.unlink()
lines=[];deadline=time.monotonic()+10
while time.monotonic()<deadline:
 for line in log.readlines():
  if '[esp32]' in line and any(x in line for x in ('DEMO STARTED:','SERVO ESTIMATE=','V14 MODE:')):lines.append(line.rstrip())
 if any('V14 MODE: exited=0' in x for x in lines):break
 time.sleep(0.1)
assert any('V14 MODE: exited=0' in x and 'inspect_lock=0' in x for x in lines)
states=[]
for _ in range(3):
 with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:d=json.load(response)
 e=d.get('esp32',{})
 states.append({'connected':e.get('connected'),'stale':e.get('stale'),'last_telemetry_at':e.get('last_telemetry_at'),'bench_state':d.get('bench_state'),'button':d.get('manual_button')})
 time.sleep(1)
units=['for-cat-api.service','for-cat-esp32-bridge.service','for-cat-ai.service']
p=subprocess.run(['systemctl','--user','is-active',*units],capture_output=True,text=True)
result={'services':dict(zip(units,p.stdout.splitlines())),'ack_lines':lines,'samples':states,'movement_commands_sent_by_agent':False,'physical_button_retest_pending':True}
(r/'resume_status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert p.returncode==0 and states[-1]['connected'] is True and states[-1]['stale'] is False
assert states[-1]['last_telemetry_at']!=states[0]['last_telemetry_at']
