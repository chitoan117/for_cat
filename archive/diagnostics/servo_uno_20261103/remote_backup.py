from pathlib import Path
import subprocess,hashlib,json,struct

r=Path('/home/toan/for_cat/evidence/servo_uno_20261103_deploy')
tool='/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/flash_tool/bin/esptool.py'
expected='4c6c1d472d1be303c92b0bf4b5485b3f1669957396a0cb8de24c609f49a4fef8'
assert hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest()==expected,'Firmware transfer hash mismatch'
assert not (r/'before_flash_0_150000.bin').exists(),'Backup already exists; do not overwrite'
subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True)
owners=subprocess.run(['fuser','/dev/ttyACM0'],capture_output=True,text=True)
assert owners.returncode==1 and not owners.stdout.strip(),'Serial port still has an owner: '+owners.stdout+owners.stderr
with (r/'backup.log').open('w') as log:
    result=subprocess.run([tool,'--chip','esp32s3','--port','/dev/ttyACM0','--baud','921600','--before','default-reset','--after','no-reset','read-flash','0x0','0x150000',str(r/'before_flash_0_150000.bin')],stdout=log,stderr=subprocess.STDOUT,timeout=180)
if result.returncode:
    print((r/'backup.log').read_text()[-3500:])
    raise SystemExit(result.returncode)
data=(r/'before_flash_0_150000.bin').read_bytes()
assert len(data)==0x150000
table=data[0x8000:0x8c00]
expected_table=(r/'esp32.ino.partitions.bin').read_bytes()
meta={'backup_bytes':len(data),'backup_sha256':hashlib.sha256(data).hexdigest(),
      'partition_table_matches':table==expected_table,
      'ota_data_erased':data[0xe000:0x10000]==b'\xff'*0x2000,
      'app0_magic':data[0x10000],
      'nvs_sha256':hashlib.sha256(data[0x9000:0xe000]).hexdigest()}
(r/'nvs_before.bin').write_bytes(data[0x9000:0xe000])
(r/'preflash.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
assert meta['partition_table_matches'],'Partition table differs; inspect before programming'
assert meta['ota_data_erased'],'Non-default OTA selection; inspect before programming'
assert meta['app0_magic']==0xe9,'App0 is not the expected image'
print('BACKUP_READY; bridge stopped; chip remains in flashing mode, no application started')
