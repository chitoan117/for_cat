from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent;dest=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(dest.read_bytes()).hexdigest()==(r/'before_source.sha256').read_text().strip()
result=json.loads((r/'flash_result.json').read_text())
assert result['app_verified'] and result['nvs_preserved']
shutil.copy2(r/'esp32/esp32.ino',dest)
print('Verified trial source synchronized:',dest)
