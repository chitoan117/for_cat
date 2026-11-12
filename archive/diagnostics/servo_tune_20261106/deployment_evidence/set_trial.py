from pathlib import Path
import os,time,json
r=Path('/home/toan/for_cat/evidence/servo_tune_20261106');r.mkdir(exist_ok=True)
cmd=Path('/tmp/for_cat_cmd.txt')
deadline=time.monotonic()+5
while cmd.exists() and time.monotonic()<deadline:time.sleep(0.1)
assert not cmd.exists(),'Another command is pending'
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/for_cat_tune_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('close_ms 1000\nservo_position\nmode\n')
 os.link(tmp,cmd)
finally:
 if tmp.exists():tmp.unlink()
lines=[];deadline=time.monotonic()+10
while time.monotonic()<deadline:
 for line in log.readlines():
  if '[esp32]' in line and any(x in line for x in ('SERVO CLOSE DURATION','Invalid ms:','SERVO ESTIMATE=','V14 MODE:')):lines.append(line.rstrip())
 if any('SERVO ESTIMATE=' in x and 'close_ms=1000' in x for x in lines) and any('V14 MODE:' in x for x in lines):break
 time.sleep(0.1)
result={'trial_close_ms':1000,'open_ms':1100,'movement_commands_sent':False,'ram_only':True,'owner_report':'drifts toward OPEN; stationary at neutral','ack_lines':lines}
(r/'trial_setting.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert any('SERVO CLOSE DURATION UPDATED' in x for x in lines)
assert any('SERVO ESTIMATE=' in x and 'close_ms=1000' in x and 'moving=0' in x for x in lines)
