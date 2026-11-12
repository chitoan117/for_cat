from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='aa5060d9c7febfc7a958135007e4bf0c768b795c5c4d42683f71e5c35ff75fef'
shutil.copy2(r/'esp32/PumpFill59Gate.h',p.parent/'PumpFill59Gate.h')
p.write_bytes((r/'esp32/esp32.ino').read_bytes())
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
print('Source synchronized, scale calibration untouched.')
