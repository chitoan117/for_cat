import hashlib,json,shutil
from pathlib import Path
OUT=Path(r'D:\for_cat\FRONTEND_USER_APP_OFFLINE_20261026');SRC=Path(r'D:\DA_KT_NC\feeder_demo');BASE=Path(r'D:\for_cat')
assert OUT.is_dir() and not (OUT/'frontend_original').exists()
files=[p for folder in ('lib','test','web') for p in (SRC/folder).rglob('*') if p.is_file()]+[SRC/n for n in ('pubspec.yaml','pubspec.lock','analysis_options.yaml','README.md')]
hashes={}
for p in files:
 n=p.relative_to(SRC);dest=OUT/'frontend_original'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[n.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'frontend_before_sha256.json').write_text(json.dumps(hashes,indent=2))
V=OUT/'verification';V.mkdir()
ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','.venv','data','*.db','*.db-*','*.engine','*.onnx','*.pt','*.pth','cat_dog_trt','*.bin','*.exe')
shutil.copytree(BASE/'jetson',V/'jetson',ignore=ignore)
shutil.copytree(BASE/'scripts',V/'scripts',ignore=ignore)
shutil.copy2(BASE/'pytest.ini',V/'pytest.ini')
overlays=[BASE/'OFFLINE_REVIEW_20261024/handoff/payload',BASE/'FLUTTER_REAL_INTEGRATION_20261025/backend_payload',
 BASE/'OVERNIGHT_MEAL_PLAN_20261025/payload',BASE/'SCHEDULED_WORKER_20261026/payload',BASE/'HX711_CALIBRATION_20261026/payload']
provenance={}
for source in overlays:
 for folder in ('jetson','config'):
  if (source/folder).is_dir():
   for p in (source/folder).rglob('*'):
    if p.is_file() and p.suffix not in ('.pyc','.db','.bin','.exe'):
     n=p.relative_to(source);dest=V/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);provenance[n.as_posix()]=str(source)
(OUT/'offline_backend_provenance.json').write_text(json.dumps({'purpose':'ISOLATED_OFFLINE_VERIFICATION_NOT_DEPLOYMENT_SOURCE','base':str(BASE/'jetson'),'overlays':provenance,'excluded_unfinished_demo':True},indent=2))
print('Frontend originals:',len(files),'offline backend verification workspace:',V)
