from pathlib import Path
import hashlib,json,shutil,py_compile
r=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ('esp32.ino.bin','esp32.ino.partitions.bin'):shutil.copy2(r/'build'/n,r/n)
(r/'app.sha256').write_text(sha(r/'esp32.ino.bin')+'\n')
(r/'backend_plan.json').write_text(json.dumps({p.name:{'before':sha(r/'before'/p.name) if (r/'before'/p.name).exists() else None,'after':sha(p)} for p in (r/'backend').glob('*.py')},indent=2))
for p in list((r/'backend').glob('*.py'))+[r/'install.py',r/'deploy_firmware.py',r/'deploy_backend.py']:py_compile.compile(str(p),doraise=True)
assert all(sha(r/'esp32'/n)==sha(Path('D:/CODE_TEST_LOADCELL_CHUAN/esp32')/n) for n in ('CatNearGate.h','FallbackGate.h','D1PumpGate.h','PumpFill59Gate.h'))
(r/'integrity.json').write_text(json.dumps({'app_sha256':sha(r/'esp32.ino.bin'),'unchanged_servo_backup_pump_headers':True,'source_sha256':sha(r/'esp32/esp32.ino'),'meal_header_sha256':sha(r/'esp32/MealPreferenceGate.h')},indent=2))
print((r/'integrity.json').read_text())
