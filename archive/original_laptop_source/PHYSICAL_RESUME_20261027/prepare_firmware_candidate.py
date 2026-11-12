"""Copy reviewed reference only; never edit Jetson staged firmware or flash."""
import hashlib,json,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parent;BASE=Path(r'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_main_audit_full\esp32');DST=OUT/'firmware_candidate/esp32'
assert BASE.is_dir() and not DST.exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reference={p.relative_to(BASE).as_posix():sha(p) for p in BASE.rglob('*') if p.is_file() and not any(n in p.parts for n in ('.pio','.git','__pycache__'))}
shutil.copytree(BASE,DST,ignore=shutil.ignore_patterns('.pio','.git','__pycache__'))
manifest={'scope':'UNFLASHED_CANDIDATE_REFERENCE_NOT_DEPLOYMENT','reference_root':str(BASE),'reference_source_sha256':reference,
 'historical_installed_app_sha256':'118bfb14cb8adc3fe435857c5dc463cad4874552bba072bab482584158c326a1',
 'historical_app_is_not_fresh_flash_readback':True}
for name in ('.pio/build/diag_current_hardware/firmware.bin',):
 p=BASE/name
 if p.is_file():manifest['cached_reference_app_sha256']=sha(p)
(OUT/'firmware_candidate/reference_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'copied_source_files':len(reference),'candidate':str(DST),'cached_app_sha256':manifest.get('cached_reference_app_sha256')},indent=2))
