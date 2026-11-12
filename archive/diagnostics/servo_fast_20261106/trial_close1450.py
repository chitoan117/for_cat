from pathlib import Path
import os,time,json
r=Path('/home/toan/for_cat/evidence/servo_fast_20261106')
cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_close1450_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('open_ms 900\nclose_ms 1450\nservo_position\nmode\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+4
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
assert any('open_ms=900' in x and 'close_ms=1450' in x and 'open_us=1350' in x and 'close_us=1600' in x and 'moving=0' in x for x in lines)
result={'scope':'RAM_TRIAL_ONLY','open_us':1350,'open_ms':900,'close_us':1600,'close_ms':1450,
 'owner_feedback_previous':'900ms opening correct;1050ms closing insufficient with accumulated drift',
 'acknowledgements':lines,'movement_or_inspection_ack_command_sent':False}
(r/'trial_close1450.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
