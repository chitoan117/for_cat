from pathlib import Path
import os,time,json,urllib.request
r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106_gpio19')
cmd=Path('/tmp/for_cat_cmd.txt')
assert not cmd.exists(),'Another command pending'
log=Path('/var/log/syslog').open(errors='replace');log.seek(0,2)
tmp=Path('/tmp/forcat_pcb_readings_'+str(os.getpid())+'.txt')
try:
 with tmp.open('x') as f:f.write('sensors_on\nmode\nsensors\n')
 os.link(str(tmp),str(cmd))
finally:tmp.unlink()
lines=[];deadline=time.monotonic()+8
while time.monotonic()<deadline:
 lines.extend(x.rstrip() for x in log.readlines() if '[esp32]' in x)
 time.sleep(0.2)
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:d=json.load(response)
result={'command_ack':lines,'ultrasonic':d.get('ultrasonic'),'weight':d.get('weight'),'esp32':d.get('esp32'),'no_actuator_command':True}
(r/'readings_result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
assert any('sensor=1' in x for x in lines),'Sensor initialization not confirmed'
