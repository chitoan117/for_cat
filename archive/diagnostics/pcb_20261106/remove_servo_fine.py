from pathlib import Path
import difflib,hashlib
r=Path(__file__).parent/'servo_no_fine'
r.mkdir(exist_ok=True)
src=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino')
original=src.read_bytes()
(r/'esp32.before.ino').write_bytes(original)
s=original.decode('utf-8').replace('\r\n','\n')
before=s
for direction in ('close','open'):
    block=f'''  if (!std::strcmp(line, "servo_fine_{direction}")) {{
    bench_v8::manualServoMove({'false' if direction=='close' else 'true'}, bench_v8::SERVO_FINE_MS, s.now_ms);
    return;
  }}
'''
    assert s.count(block)==1
    s=s.replace(block,'')
replacements={
'//   open_ms 1100 / close_ms 900; 3=open, 4=close, servo_fine_open/close=170ms.':'//   open_ms 1100 / close_ms 900; 3=open, 4=close; no fine-adjust commands.',
'constexpr uint16_t SERVO_FINE_MS = 170; // Actual UNO FINE_MS.\n':'',
'STOP1500_FINE170':'STOP1500',
'      "FINE: servo_fine_close / servo_fine_open = 170ms; 0/stop = hold 1500us\\n"':'      "STOP: 0/stop = hold 1500us\\n"',
', FINE 170ms, STOP 1500us.':', STOP 1500us.',
}
for a,b in replacements.items():
    assert a in s,a
    s=s.replace(a,b)
assert 'servo_fine_' not in s and 'SERVO_FINE_MS' not in s
p=r/'esp32';p.mkdir(exist_ok=True)
(p/'esp32.ino').write_bytes(s.encode('utf-8'))
(r/'change.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='before',tofile='after')),encoding='utf-8')
print('Prepared servo-only removal; baseline SHA256',hashlib.sha256(original).hexdigest())
