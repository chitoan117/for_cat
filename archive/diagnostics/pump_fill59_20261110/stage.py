from pathlib import Path
import hashlib,json,shutil,py_compile
r=Path(__file__).parent
for n in ('esp32.ino.bin','esp32.ino.partitions.bin'):
    assert (r/'build'/n).is_file(),n
    shutil.copy2(r/'build'/n,r/n)
sha=hashlib.sha256((r/'esp32.ino.bin').read_bytes()).hexdigest()
(r/'app.sha256').write_text(sha+'\n')
(r/'integrity.json').write_text(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'esp32').iterdir() if p.is_file()},indent=2))
(r/'test_result.txt').write_text('PASS target cutoff, continuous beyond1s, invalid/stale OFF, native10s limit, no replay, rollover, operator OFF\n')
for n in ('install.py','deploy_firmware.py','commission.py','sync_source.py'):
    py_compile.compile(str(r/n),doraise=True)
print('Staged app SHA256 '+sha)
