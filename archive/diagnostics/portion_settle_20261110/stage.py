from pathlib import Path
import hashlib,json,shutil,py_compile
r=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ('esp32.ino.bin','esp32.ino.partitions.bin'):shutil.copy2(r/'build'/n,r/n)
(r/'app.sha256').write_text(sha(r/'esp32.ino.bin')+'\n')
for n in ('CatNearGate.h','FallbackGate.h','D1PumpGate.h','PumpFill59Gate.h'):
 assert sha(r/'esp32'/n)==sha(r/'before'/n),n
a=(r/'before/esp32.ino').read_text(encoding='utf8');b=(r/'esp32/esp32.ino').read_text(encoding='utf8')
cal='bool startBenchCal(BenchCal kind, double known_g, uint32_t now) {'
assert a[a.index(cal):a.index('void command(char* line, const Sample& s)')]==b[b.index(cal):b.index('void command(char* line, const Sample& s)')],'Scale routines changed'
for p in ('install.py','deploy_firmware.py'):py_compile.compile(str(r/p),doraise=True)
(r/'integrity.json').write_text(json.dumps({'app_sha256':sha(r/'esp32.ino.bin'),'source_sha256':sha(r/'esp32/esp32.ino'),'unchanged_proximity_backup_pump_headers':True,'scale_calibration_code_identical':True,'headers':{p.name:sha(p) for p in (r/'esp32').glob('*.h')}},indent=2))
print((r/'integrity.json').read_text())
