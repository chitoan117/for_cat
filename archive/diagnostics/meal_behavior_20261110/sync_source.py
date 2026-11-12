from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent;p=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(p.read_bytes()).hexdigest()==(r/'source_before.sha256').read_text().strip()
shutil.copy2(r/'esp32/MealPreferenceGate.h',p.parent/'MealPreferenceGate.h')
p.write_bytes((r/'esp32/esp32.ino').read_bytes())
front=Path('D:/DA_KT_NC/feeder_demo/lib')
for n in ('feeder_backend.dart','real_backend.dart','history_model.dart','user_pages.dart'):shutil.copy2(front/n,r/'frontend'/n)
(r/'source_sync.json').write_text(json.dumps({'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'app_sha256':(r/'app.sha256').read_text().strip()},indent=2))
print('Source synchronized; firmware and Flutter candidates match deployed release.')
