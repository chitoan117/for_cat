from pathlib import Path
import hashlib
r=Path(__file__).parent;out=r/'balanced';(out/'esp32').mkdir(parents=True,exist_ok=True)
s=(r/'esp32/esp32.ino').read_text()
assert 'uint16_t open_ms = 750;' in s and 'uint16_t close_ms = 1050;' in s
s=s.replace('uint16_t open_ms = 750;', 'uint16_t open_ms = 900;').replace('uint16_t close_ms = 1050;', 'uint16_t close_ms = 1450;')
s=s.replace('(+50ms).','(owner-supervised relative travel calibration).')
s=s.replace('open_ms 750','open_ms 900').replace('close_ms 1050','close_ms 1450')
s=s.replace('1350us 750ms','1350us 900ms').replace('1600us 1050ms','1600us 1450ms')
s=s.replace('1350us/750ms','1350us/900ms').replace('1600us/1050ms','1600us/1450ms')
(out/'esp32/esp32.ino').write_text(s)
t=(r/'test_servo.py').read_text().replace('open_ms==750&&close_ms==1050','open_ms==900&&close_ms==1450')
(out/'test_servo.py').write_text(t)
d=(r/'deploy_servo.py').read_text().replace("r=Path('/home/toan/for_cat/evidence/servo_fast_20261106')", "r=Path('/home/toan/for_cat/evidence/servo_balanced_20261106')")
d=d.replace('/evidence/pcb_pin_fix_20261106_gpio19/esp32.ino.bin','/evidence/servo_fast_20261106/esp32.ino.bin')
d=d.replace('70e5d5aacf62810e2ae721f2b079854427f12c16103d3ab704b011980a6293d8','1d5b96fd8e87d219afef7e44c17e0dc2db5a3bac46114a158ddb5b4d480c0c50')
(out/'deploy_servo.py').write_text(d)
print('Staged900/1450; pending physical acceptance; not compiled/flashed/synced to main.')
