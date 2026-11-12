from pathlib import Path
import hashlib,json
r=Path(__file__).parent
p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='215e0751b82603b60eb9cd8a7c2ecf6a6a586d9858dd1da37387c160ec640fca','Source changed; no overwrite'
updated=(r/'esp32/esp32.ino').read_bytes()
p.write_bytes(updated)
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(updated).hexdigest(),'app_sha256':(r/'app.sha256').read_text(),'status':'FLASH_VERIFIED_NVS_PRESERVED_PUMP_OFF_WAIT_OWNER_COMMAND'},indent=2))
print('Source synchronized to flashed pump-bench firmware; no hardware command.')
