from pathlib import Path
import shutil,hashlib,json
r=Path('D:/Agent_Cat/diagnostics/servo_fast_20261106');r.mkdir(exist_ok=True)
src=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
raw=src.read_bytes();(r/'before.ino').write_bytes(raw);s=raw.decode('utf-8').replace('\r\n','\n')
changes={
 'constexpr uint16_t SERVO_OPEN_US = 1400; // UNO-tested: open RIGHT.':'constexpr uint16_t SERVO_OPEN_US = 1350; // Faster OPEN trial; needs physical travel verification.',
 'uint16_t open_ms = 1100; // Actual UNO OPEN_MS, not its outdated menu text.':'uint16_t open_ms = 750; // Shorter OPEN for the faster pulse; initial physical trial.',
 'uint16_t close_ms = 1000; // Closing-duration calibration: owner reports short closing, neutral stationary.':'uint16_t close_ms = 1050; // Owner requested a small additional closing travel (+50ms).',
}
for old,new in changes.items():assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('1400us OPEN RIGHT','1350us OPEN RIGHT').replace('open_ms 1100 / close_ms 1000','open_ms 750 / close_ms 1050')
s=s.replace('RIGHT 1400us 1100ms','RIGHT 1350us 750ms').replace('LEFT 1600us 1000ms','LEFT 1600us 1050ms')
s=s.replace('open_ms 1100, close_ms 1000','open_ms 750, close_ms 1050')
s=s.replace('OPEN RIGHT 1400us/1100ms, CLOSE LEFT 1600us/1000ms','OPEN RIGHT 1350us/750ms, CLOSE LEFT 1600us/1050ms')
s=s.replace('moving=%d open_ms=%u close_ms=%u\\n','moving=%d open_ms=%u close_ms=%u open_us=%u close_us=%u\\n')
s=s.replace('unsigned(bench_v8::open_ms),unsigned(bench_v8::close_ms));',
 'unsigned(bench_v8::open_ms),unsigned(bench_v8::close_ms),unsigned(bench_v8::SERVO_OPEN_US),unsigned(bench_v8::SERVO_CLOSE_US));')
(r/'esp32').mkdir(exist_ok=True);(r/'esp32/esp32.ino').write_text(s,encoding='utf-8')
t=Path('D:/Agent_Cat/diagnostics/pcb_pin_fix_20261106/test_servo.py').read_text()
t=t.replace('open_ms==1100&&close_ms==1000','open_ms==750&&close_ms==1050').replace('SERVO_OPEN_US==1400','SERVO_OPEN_US==1350')
(r/'test_servo.py').write_text(t)
# Reuse the guarded flash procedure against the actual currently installed app.
d=Path('D:/Agent_Cat/diagnostics/pcb_pin_fix_20261106/final/deploy_servo.py').read_text()
d=d.replace("r=Path('/home/toan/for_cat/evidence/pcb_pin_fix_20261106_gpio19')","r=Path('/home/toan/for_cat/evidence/servo_fast_20261106')")
d=d.replace('/evidence/pcb_pin_fix_20261106/esp32.ino.bin','/evidence/pcb_pin_fix_20261106_gpio19/esp32.ino.bin')
d=d.replace('e1c8519d02234cd975ad92f75c7edfc1d2ca77a70b7626f3d5f5f86e10629738','70e5d5aacf62810e2ae721f2b079854427f12c16103d3ab704b011980a6293d8')
(r/'deploy_servo.py').write_text(d)
(r/'before_source.sha256').write_text(hashlib.sha256(raw).hexdigest())
print('Trial profile:1350us/750ms open,1600us/1050ms close;neutral1500us. No physical test claimed.')
