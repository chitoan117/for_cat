from pathlib import Path
import json,time,subprocess,serial
r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106_gpio19')
subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
frames=[];lines=[]
try:
 s=serial.Serial(None,115200,timeout=0.1);s.dtr=False;s.rts=False;s.port='/dev/ttyACM0';s.open()
 try:
  s.write(b'servo_position\nmode\nsensors\n')
  deadline=time.monotonic()+6
  while time.monotonic()<deadline:
   line=s.readline().decode('utf-8',errors='replace').strip()
   if line:
    lines.append(line)
    try:
     d=json.loads(line)
     if d.get('type')=='status':frames.append(d)
    except (ValueError,AttributeError):pass
  assert frames, 'No fresh UART telemetry'
  d=frames[-1]
  assert d.get('pcb_profile')=='HCSR04_E1_E2_D1_D2_PINFIX'
  assert d.get('close_trigger_g')==35
  assert all(k in d for k in ['pcb_e1_cat_cm','pcb_e2_food_cm','pcb_d1_bowl_cm','pcb_d2_tank_cm'])
  result={'profile':d['pcb_profile'],'close_trigger_g':d['close_trigger_g'],'oled_ok':d.get('oled_ok'),
    'distances_cm':{k:d.get(k) for k in ['pcb_e1_cat_cm','pcb_e2_food_cm','pcb_d1_bowl_cm','pcb_d2_tank_cm']},
    'diagnostic_lines':[x for x in lines if any(v in x for v in ['SERVO ESTIMATE=','V14 MODE:','E1_CAT/'])],
    'movement_commands_sent':False}
  (r/'pcb_uart_result.json').write_text(json.dumps(result,indent=2))
  (r/'pcb_uart.log').write_text('\n'.join(lines)+'\n')
  print(json.dumps(result,indent=2))
 finally:s.close()
finally:subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
