"""Single diagnostic recovery after HC1 disabled between target placements; no actuators."""
import datetime,hashlib,json,subprocess,termios,time,urllib.request
from pathlib import Path
import serial
from serial.tools import list_ports
E=Path(EVIDENCE);O=E/('hc1_enable_for_20cm_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));O.mkdir()
HC='HC_SR04_1';COMMAND=b'ultra-select hc1 CONFIRM\n';frames=[];buffer=bytearray();lines=[]
result={'status':'BLOCKED','evidence':str(O),'reason':'HC1_DISABLED_BEFORE_OWNER_CONFIRMED_20CM_CAPTURE','commands':[],'actuator_commands_sent':False,'flash_performed':False}
def safe(f):
 assert f['mode']=='diag_current_hardware' and f['ultrasonic_schema_version']==1 and f['rtc_type']=='NONE'
 assert f['actuator_outputs_enabled']==0 and f['physical_pump_on'] is False
 for k in ('servo_armed','pump_armed','auto_feed','auto_water'):assert f['current_hardware'][k] is False
 assert set(f['ultrasonic'])=={HC,'HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'}
 for key,s in f['ultrasonic'].items():
  if key!=HC:assert s['enabled'] is False
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=8) as r:before=json.load(r)
assert before['data_source']=='REAL' and before['esp32']['connected']
assert before['safety']['actuator_outputs_enabled']==0 and all(before['safety'][k] is False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution'))
assert all(s['enabled'] is False for s in before['ultrasonic'].values())
ports=[p for p in list_ports.comports() if p.vid==0x1a86 and p.pid==0x55d3 and p.serial_number=='5C85066678'];assert len(ports)==1
subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
try:
 assert subprocess.run(['fuser',ports[0].device],capture_output=True).returncode==1
 with (O/'raw_serial.bin').open('xb') as raw:
  p=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1,exclusive=True);p.dtr=False;p.rts=False;p.port=ports[0].device
  with p:
   settings=termios.tcgetattr(p.fileno());settings[2]&=~termios.HUPCL;termios.tcsetattr(p.fileno(),termios.TCSANOW,settings)
   def receive(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
     chunk=p.read(min(4096,max(1,p.in_waiting)))
     if not chunk:continue
     raw.write(chunk);assert raw.tell()<262144
     for byte in chunk:
      if byte in (10,13):
       line=bytes(buffer);buffer.clear()
       if not line:continue
       lines.append(line.decode('utf-8','replace'))
       if line.startswith(b'{'):
        try:f=json.loads(line)
        except ValueError:continue
        safe(f);frames.append(f)
      else:buffer.append(byte);assert len(buffer)<=4096
   receive(3.5);assert len(frames)>=2 and all(not s['enabled'] for s in frames[-1]['ultrasonic'].values())
   p.write(COMMAND);p.flush();result['commands'].append(COMMAND.decode().strip())
   receive(4);assert frames[-1]['ultrasonic'][HC]['enabled'] is True
   assert any('ULTRA_SINGLE_ACQUISITION_ENABLED_NOT_PHYSICAL_PASS' in line for line in lines)
 result.update(status='RUNTIME_PASS',before_uptime_ms=before['esp32']['monotonic_ms'],raw_uptime_ms=frames[-1]['monotonic_ms'],hc1=frames[-1]['ultrasonic'][HC],other_channels_disabled=True)
except Exception as error:
 result['error']=str(error);raise
finally:
 subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
 if result['status']=='RUNTIME_PASS':
  ready=False
  for _ in range(30):
   try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=4) as r:s=json.load(r)
    if s['esp32']['connected'] and s['ultrasonic'][HC]['enabled'] is True:ready=True;break
   except Exception:pass
   time.sleep(.5)
  result['rest_recovered']=ready
  if not ready:result.update(status='BLOCKED',error='REST not recovered after diagnostic handoff')
 (O/'raw_frames.json').write_text(json.dumps(frames,indent=2));(O/'serial_lines.log').write_text('\n'.join(lines)+'\n')
 (O/'summary.json').write_text(json.dumps(result,indent=2));(O/'manifest_sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file()},indent=2));print(json.dumps(result,indent=2))
