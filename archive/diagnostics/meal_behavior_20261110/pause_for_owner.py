from pathlib import Path
import os,time,json
r=Path(__file__).parent
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
p=Path('/tmp/fc_owner_pause_'+str(os.getpid())+'.txt')
with p.open('x') as f:f.write('pump_auto off\npump_off\n0\nmode\npump_status\n')
try:os.link(str(p),'/tmp/for_cat_cmd.txt')
finally:p.unlink()
time.sleep(3)
with open('/var/log/syslog','rb') as f:f.seek(offset);lines=f.read().decode('utf8','replace').splitlines()
lines=[s for s in lines if '[esp32]' in s]
result={'owner_requested_pause':True,'pump_off_ack':any('PUMP OFF GPIO7 LOW.' in s for s in lines),
 'demo_paused_ack':any('EXIT 0' in s for s in lines),
 'servo_idle_ack':any('servo_moving=0' in s and 'exited=1' in s for s in lines),'log':lines}
(r/'paused_for_morning.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
assert result['pump_off_ack'] and result['demo_paused_ack'] and result['servo_idle_ack']
