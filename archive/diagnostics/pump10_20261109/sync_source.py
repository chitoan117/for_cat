from pathlib import Path
import hashlib,json
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='52c326b25ebbb8c7162b31c9aa0a9fed4b564622dddd304f4339fb753e68cdf4'
data=(r/'esp32/esp32.ino').read_bytes();p.write_bytes(data)
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(data).hexdigest(),'app_sha256':(r/'app.sha256').read_text()},indent=2))
print('Synchronized10s source; no hardware commands.')
