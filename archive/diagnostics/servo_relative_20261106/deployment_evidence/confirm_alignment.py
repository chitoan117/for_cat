from pathlib import Path
import os,time,json
r=Path('/home/toan/for_cat/evidence/servo_relative_20261106')
cmd=Path('/tmp/for_cat_cmd.txt')
deadline=time.monotonic()+5
while cmd.exists() and time.monotonic()<deadline:time.sleep(0.1)
assert not cmd.exists(),'Another command is pending; do not overwrite it'
log=Path('/var/log/syslog').open(errors='replace')
log.seek(0,2)
tmp=Path('/tmp/for_cat_alignment_'+str(os.getpid())+'.txt')
commands='inspect_ok\nstart\nservo_position\nmode\n'
try:
 with tmp.open('x') as f:f.write(commands)
 os.link(tmp,cmd) # Publish complete commands atomically without overwriting another file.
finally:
 if tmp.exists():tmp.unlink()
lines=[]
deadline=time.monotonic()+10
while time.monotonic()<deadline:
 for line in log.readlines():
  if '[esp32]' in line and any(x in line for x in ('BENCH INSPECT ACK:','DEMO STARTED:','SERVO ESTIMATE=','V14 MODE:')):
   lines.append(line.rstrip())
 if any('SERVO ESTIMATE=CLOSED' in x for x in lines) and any('V14 MODE: exited=0' in x for x in lines):break
 time.sleep(0.1)
result={'owner_confirmed_physically_aligned_closed':True,'commands':commands.splitlines(),'servo_movement_commands_sent':False,'ack_lines':lines}
(r/'owner_alignment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert any('operator confirms gate aligned CLOSED' in x for x in lines)
assert any('SERVO ESTIMATE=CLOSED feedback=NONE inspect_lock=0 moving=0' in x for x in lines)
assert any('V14 MODE: exited=0' in x for x in lines)
