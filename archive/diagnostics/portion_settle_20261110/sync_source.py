from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()==(r/'source_before.sha256').read_text().strip()
for n in ('MealPreferenceGate.h','PortionSettleGate.h'):shutil.copy2(r/'esp32'/n,p.parent/n)
p.write_bytes((r/'esp32/esp32.ino').read_bytes())
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'app_sha256':(r/'app.sha256').read_text().strip()},indent=2))
print('Canonical source synchronized; existing servo/proximity/pump/backup parameters retained.')
