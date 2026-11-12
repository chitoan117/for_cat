from pathlib import Path
import hashlib,shutil
r=Path(__file__).parent
d=Path('D:/Agent_Cat/diagnostics/servo_fast_20261106/balanced/deploy_servo.py').read_text()
d=d.replace("r=Path('/home/toan/for_cat/evidence/servo_balanced_20261106')","r=Path('/home/toan/for_cat/evidence/schedule_oled_20261106')")
d=d.replace('/evidence/servo_fast_20261106/esp32.ino.bin','/evidence/servo_balanced_20261106/esp32.ino.bin')
d=d.replace('1d5b96fd8e87d219afef7e44c17e0dc2db5a3bac46114a158ddb5b4d480c0c50','a23efe87f2d502f0f4aad27a0aab5cf2b140b04a06ba2f5e8f4bdf878da2aa47')
(r/'deploy_firmware.py').write_text(d)
for name in ['esp32.ino.bin','esp32.ino.partitions.bin']:shutil.copy2(r/'build'/name,r/name)
(r/'app.sha256').write_text(hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest())
