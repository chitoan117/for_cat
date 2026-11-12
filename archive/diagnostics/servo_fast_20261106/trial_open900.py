from pathlib import Path
import os,time,json
r=Path('/home/toan/for_cat/evidence/servo_fast_20261106')
cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_open900_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('open_ms 900\nservo_position\nmode\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+4
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
assert any('open_ms=900' in x and 'close_ms=1050' in x and 'open_us=1350' in x and 'moving=0' in x for x in lines)
result={'scope':'RAM_TRIAL_ONLY','open_us':1350,'open_ms':900,'close_us':1600,'close_ms':1050,
 'owner_feedback_previous':'Opening insufficient; closing returns correctly','acknowledgements':lines,'movement_command_sent':False}
(r/'trial_open900.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
