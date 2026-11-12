from pathlib import Path
import hashlib, shutil
r=Path(__file__).parent
oldroot=Path('D:/Agent_Cat/diagnostics/servo_tune_20261106')
s=(oldroot/'deploy_servo.py').read_text()
s=s.replace("r=Path('/home/toan/for_cat/evidence/servo_tune_20261106')", "r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106')")
s=s.replace("/evidence/servo_button_20261106/esp32.ino.bin", "/evidence/servo_tune_20261106/esp32.ino.bin")
s=s.replace('b88c1aa94df1e1a617405a56effd53a4930bc27246db125b26446bc98dc0984b','8ceb43f5f4939d75b50e25bef8bd226c91c5eaffb4106959f62aaf90a346113a')
(r/'deploy_servo.py').write_text(s)
s=(oldroot/'resume_verify.py').read_text().replace('/evidence/servo_tune_20261106','/evidence/pcb_pin_fix_20261106')
s=s.replace("'owner_confirmed_5_cycles_before_flash':True", "'pcb_pin_fix_verified':True")
(r/'resume_verify.py').write_text(s)
for name in ['esp32.ino.bin','esp32.ino.partitions.bin']:
    shutil.copy2(r/'build'/name,r/name)
(r/'app.sha256').write_text(hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest())
print('Prepared guarded app-only flash; NVS and old app backup required.')
