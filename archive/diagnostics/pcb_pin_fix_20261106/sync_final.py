from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).parent
dest=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert hashlib.sha256(dest.read_bytes()).hexdigest()=='172870c0ae6872fb9f2b5a8f644ff91f976b58841a5b9f4387259948b6436811'
result=json.loads((r/'final/flash_result.json').read_text())
assert result['app_verified'] and result['nvs_preserved']
shutil.copy2(r/'esp32/esp32.ino',dest)
print('Final GPIO19-aware source saved:',dest)
