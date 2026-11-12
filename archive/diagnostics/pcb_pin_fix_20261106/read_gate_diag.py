from pathlib import Path
import os,time
cmd=Path('/tmp/for_cat_cmd.txt');assert not cmd.exists()
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_diag_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('mode\nservo_position\nweight\nsensors\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+4
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x);time.sleep(.1)
out=Path('/home/toan/for_cat/evidence/cat_gate_check_20261106/diagnostic.log')
out.write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
