from pathlib import Path
import os,time,re,json
r=Path('/home/toan/for_cat/evidence/water_pulse59_latched_20261109')
def send(body):
 p=Path('/tmp/fc_pulse_commission_'+str(os.getpid())+'.txt')
 with p.open('x') as f:f.write(body+'\n')
 try:os.link(str(p),'/tmp/for_cat_cmd.txt')
 finally:p.unlink()
def tail(offset):
 with open('/var/log/syslog','rb') as f:f.seek(offset);return f.read().decode('utf-8','replace')
with open('/var/log/syslog','rb') as f:f.seek(0,2);offset=f.tell()
send('0\npump_reset\npump_driver_verified\npump_auto on\npump_status')
time.sleep(3)
text=tail(offset);assert 'PUMP AUTO ARMED:' in text,text[-2500:]
deadline=time.monotonic()+40;last=None;printed=None;outcome='ARMED_WAITING'
while time.monotonic()<deadline:
 text=tail(offset)
 matches=re.findall(r'PUMP auto=(\d) running=(\d) test=(\d) fault=(\d) driver_verified=(\d) reason=(\S+) D1=([-\d.]+) pulses=(\d+)',text)
 if matches:
  last=matches[-1]
  if last!=printed:print(json.dumps({'running':last[1],'fault':last[3],'reason':last[5],'cm':last[6],'pulses':last[7]}),flush=True);printed=last
  if last[3]=='1':outcome='FAULT_'+last[5];break
  if int(last[7])>0 and last[1]=='0' and last[5]=='TARGET_59CM':outcome='TARGET_REPORTED';break
 send('pump_status');time.sleep(.5)
result={'outcome':outcome,'last_status':last,'pulse_ms':1000,'settle_ms':5000,'max_pulses_per_arm':3,
 'trigger_band_cm':[6.1,6.4],'stop_lte_cm':5.9,'height_per_pulse_not_guaranteed':True,
 'startup_auto':False,'log':[x for x in tail(offset).splitlines() if '[esp32]' in x]}
(r/'commission_result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='log'}),flush=True)
