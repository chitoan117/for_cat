"""Snapshot existing AI validation and portable Flutter dependencies; no tests/device."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
R2=ROOT.parents[1]/'CANDIDATE_R2_OFFLINE_HARDENING_20261030'
source=R2/'candidate/backend/app/ai_frame_contract.py'
target=ROOT/'backend/ai_contract.py'
with target.open('xb') as f:f.write(source.read_bytes())
(ROOT/'AI_SOURCE.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'changes':False,'model_training':False},indent=2)+'\n')
flutter=ROOT/'flutter';flutter.mkdir();(flutter/'lib').mkdir();(flutter/'test').mkdir()
(flutter/'pubspec.yaml').write_text('''name: for_cat_closed_loop_offline
description: Optional closed-loop result view over existing FOR_CAT UI.
publish_to: none
environment:
  sdk: '>=3.8.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  feeder_demo:
    path: ../flutter_shared
dev_dependencies:
  flutter_test:
    sdk: flutter
''')
shutil.copyfile(R2/'candidate/flutter/pubspec.lock',flutter/'pubspec.lock')
print('Prepared existing AI validator and Flutter harness; no production operation.')
