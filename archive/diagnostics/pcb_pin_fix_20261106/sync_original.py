from pathlib import Path
import hashlib,shutil
r=Path(__file__).parent
dest=Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino')
assert dest.read_bytes()==(r/'local_pending_before.ino').read_bytes(),'Original source changed during work'
assert (r/'flash_result.json').is_file(),'Confirm successful verified flash first'
shutil.copy2(r/'esp32/esp32.ino',dest)
print('Original source synchronized:',dest,hashlib.sha256(dest.read_bytes()).hexdigest())
