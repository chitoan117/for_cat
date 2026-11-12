from pathlib import Path
import sys,subprocess,hashlib,json,struct,zlib,time
import serial

r=Path('/home/toan/for_cat/evidence/water_pulse_20261109')
tool='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
old=Path('/home/toan/for_cat/evidence/d1_full215_20261109/esp32.ino.bin').read_bytes()
assert hashlib.sha256(old).hexdigest()=='596317248ba2709d7f480c705d676187062bdd85fb24683ed31add216743cb25'
base=[tool,'--chip','esp32s3','--port','/dev/ttyACM0','--baud','921600','--before','default-reset','--after','no-reset']
def run(label,args):
 with (r/(label+'.log')).open('w') as f:
  p=subprocess.run(base+args,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 if p.returncode:
  print((r/(label+'.log')).read_text()[-2000:],flush=True)
  raise RuntimeError(label+' failed')
 print(label+': PASS',flush=True)

def reset_stop_and_observe(new):
 s=serial.Serial(None,115200,timeout=0.1)
 s.dtr=False;s.rts=False;s.port='/dev/ttyACM0';s.open()
 try:
  s.rts=True;time.sleep(0.1);s.rts=False
  deadline=time.monotonic()+40;lines=[];last_zero=0;last_query=0;query_sent=False
  while time.monotonic()<deadline:
   t=time.monotonic()
   # STOP only. Never assert an unobserved physical CLOSED position.
   if t-last_zero>0.5 and not query_sent:
    s.write(b'0\n');last_zero=t
   if query_sent and t-last_query>2:
    s.write(b'servo_position\nmode\nhx_diag\n');last_query=t
   line=s.readline().decode('utf-8',errors='replace').strip()
   if line:
    lines.append(line)
    if 'EXIT 0' in line and not query_sent:
     s.write(b'servo_position\nmode\nhx_diag\n');query_sent=True
    if new and 'SERVO ESTIMATE=' in line and 'feedback=NONE' in line and 'moving=0' in line and query_sent:
     break
  (r/('boot_new.log' if new else 'boot_restore.log')).write_text('\n'.join(lines)+'\n')
  profile=any('SERVO UNO PROFILE:' in x for x in lines)
  position=next((x for x in lines if 'SERVO ESTIMATE=' in x),None)
  stopped=any('EXIT 0' in x for x in lines)
  if new:
   assert stopped and position and 'feedback=NONE' in position and 'moving=0' in position,'New stopped firmware not observed'
  print(json.dumps({'new':new,'profile_seen':profile,'stop_ack':stopped,'servo_position':position,'movement_commands_sent':False}),flush=True)
  return lines
 finally:s.close()

if sys.argv[1]=='backup':
 assert not (r/'before_flash.bin').exists(),'Backup already exists'
 subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
 try:
  owner=subprocess.run(['fuser','/dev/ttyACM0'],capture_output=True,text=True)
  assert owner.returncode==1 and not owner.stdout.strip(),'UART owned: '+owner.stdout+owner.stderr
  run('read_backup',['read-flash','0x0','0x150000',str(r/'before_flash.bin')])
  b=(r/'before_flash.bin').read_bytes()
  assert len(b)==0x150000
  assert b[0x10000:0x10000+len(old)]==old,'Actual app differs from the known source baseline; no flash permitted'
  assert b[0x8000:0x8c00]==(r/'esp32.ino.partitions.bin').read_bytes(),'Partition table mismatch'
  seq=[]
  for off in (0xe000,0xf000):
   entry=b[off:off+32]
   n=struct.unpack_from('<I',entry)[0];state=struct.unpack_from('<I',entry,24)[0];crc=struct.unpack_from('<I',entry,28)[0]
   assert crc==zlib.crc32(entry[:4],0xffffffff) and state==0xffffffff,'Unexpected OTA metadata'
   seq.append(n)
  assert seq==[1,0],'Unexpected active OTA selection'
  (r/'nvs_before.bin').write_bytes(b[0x9000:0xe000])
  result={'actual_baseline_matches':True,'partition_table_matches':True,'ota_sequences':seq,'backup_sha256':hashlib.sha256(b).hexdigest(),'nvs_sha256':hashlib.sha256(b[0x9000:0xe000]).hexdigest()}
  (r/'backup_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 except BaseException:
  reset_stop_and_observe(False)
  subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'])
  raise
elif sys.argv[1]=='flash':
 assert json.loads((r/'backup_result.json').read_text())['actual_baseline_matches']
 expected=(r/'app.sha256').read_text().strip()
 assert hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest()==expected
 restored_or_new=False
 try:
  run('write_servo_app',['write-flash','0x10000',str(r/'esp32.ino.bin')])
  run('verify_servo_app',['verify-flash','0x10000',str(r/'esp32.ino.bin')])
  run('read_nvs_after',['read-flash','0x9000','0x5000',str(r/'nvs_after.bin')])
  assert (r/'nvs_before.bin').read_bytes()==(r/'nvs_after.bin').read_bytes(),'NVS changed'
  reset_stop_and_observe(True)
  result={'app_sha256':expected,'app_verified':True,'nvs_preserved':True,'servo_movement_commands_sent':False,'demo_exited_until_owner_aligns_gate':True}
  (r/'flash_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
  restored_or_new=True
 except BaseException:
  # Restore only the original app slot if the new programming/boot checks fail.
  (r/'restore_old_app.bin').write_bytes(old)
  run('rollback_old_app',['write-flash','0x10000',str(r/'restore_old_app.bin')])
  run('verify_rollback',['verify-flash','0x10000',str(r/'restore_old_app.bin')])
  reset_stop_and_observe(False)
  restored_or_new=True
  raise
 finally:
  if restored_or_new:
   subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True)
else:raise ValueError('backup or flash required')
