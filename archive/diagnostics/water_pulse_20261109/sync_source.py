from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='09880c1bc3e8d18d9e30999c275c0b40fc33983be29e488a1ae1e9bce1e2be9d'
data=(r/'esp32/esp32.ino').read_bytes()
shutil.copy2(r/'esp32/D1PumpGate.h',p.parent/'D1PumpGate.h')
p.write_bytes(data)
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(data).hexdigest(),'header_sha256':hashlib.sha256((p.parent/'D1PumpGate.h').read_bytes()).hexdigest(),'app_sha256':(r/'app.sha256').read_text()},indent=2))
print('Synchronized source and new header; no hardware command.')
