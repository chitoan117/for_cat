from pathlib import Path
import hashlib,json
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='a4cae90067fdf965157e1d15ad2cf6a2da78c7405608ec26559078d5527fdf52'
data=(r/'esp32/esp32.ino').read_bytes();p.write_bytes(data)
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(data).hexdigest(),'app_sha256':(r/'app.sha256').read_text()},indent=2))
print('Source synchronized to native-duration firmware.')
