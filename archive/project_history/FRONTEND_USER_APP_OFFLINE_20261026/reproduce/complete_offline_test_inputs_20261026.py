from pathlib import Path
import shutil
import json,hashlib
BASE=Path(r'D:\for_cat');V=BASE/'FRONTEND_USER_APP_OFFLINE_20261026/verification'
for p in (BASE/'ai').rglob('*.py'):
 if any(part in ('__pycache__','datasets','models','.venv') for part in p.relative_to(BASE/'ai').parts):continue
 target=V/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for p in (BASE/'docs').rglob('*'):
 if p.is_file() and p.suffix in ('.md','.csv','.json'):
  target=V/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
print('Local code/static test fixtures copied; no models/datasets/devices touched.')
archive=Path(r'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_overnight_stage')
provenance=json.loads((V.parent/'offline_backend_provenance.json').read_text())
sources=[(archive/'jetson/app/api/routes.py',V/'jetson/app/api/routes.py'),
         (archive/'jetson/app/api/esp32_routes.py',V/'jetson/app/api/esp32_routes.py'),
         (archive/'jetson/app/models.py',V/'jetson/app/models.py'),
         (BASE/'OFFLINE_REVIEW_20261024/project/esp32/platformio.ini',V/'esp32/platformio.ini')]
for root in (BASE/'FEED_NOW_DRY_RUN_20261025/payload',BASE/'BUTTON_LATENCY_FIX_20261025/payload'):
 for p in (root/'jetson/app/web').rglob('*'):
  if p.is_file(): sources.append((p,V/p.relative_to(root)))
for source,target in sources:
 if not source.is_file():continue
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 provenance['overlays'][str(target.relative_to(V))]={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(V.parent/'offline_backend_provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print('Restored archived canonical routes and missing static web/ini fixtures in verification only.')
