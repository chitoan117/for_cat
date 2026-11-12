from pathlib import Path
import time,os,json,urllib.request
r=Path('/home/toan/for_cat/evidence/servo_fast_20261106')
cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_fast_align_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('0\ninspect_ok\nmode\nservo_position\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+5
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
assert any('BENCH INSPECT ACK:' in x for x in lines)
assert any('SERVO ESTIMATE=CLOSED' in x and 'moving=0' in x and 'open_ms=750' in x and 'close_ms=1050' in x and 'open_us=1350' in x and 'close_us=1600' in x for x in lines)
assert any('exited=1' in x and 'inspect_lock=0' in x for x in lines)
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:d=json.load(response)
result={'owner_confirmed_unjammed_and_closed':True,'acknowledgements':lines,
 'automatic_ai_demo_exited_for_supervised_trial':True,'movement_commands_sent':False,
 'weight_grams':d.get('grams')}
(r/'trial_ready.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
