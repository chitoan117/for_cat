"""Collect existing Phase4 evidence/hashes only; no new tests, staging or devices."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent
OUT=HERE/'phase4'
ROOT=HERE.parent
FE=Path(r'D:\DA_KT_NC\feeder_demo')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
backend=load('backend_result.json');flutter=load('flutter_result.json');build=load('build_result.json')
python_count=int(re.search(r'(\d+) passed',backend['stdout']).group(1))
flutter_count=int(re.search(r'\+(\d+): All tests passed',flutter['stdout']).group(1))
assert python_count==36 and flutter_count==33
assert 'No issues found!' in flutter['analyze']
assert backend['api_fixture_sha256']==sha(OUT/'api_contract_fixture.json')
for mode in ('real','mock'):
    assert sha(OUT/('web_'+mode)/'main.dart.js')==build[mode]['main_dart_js_sha256']
files=[ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/ai_state.py',
       HERE/'test_phase4_api.py',HERE/'phase4_verify.py',HERE/'phase4_evidence.py']
files += [FE/p for p in ('lib/feeder_state.dart','lib/live_camera_controller.dart','lib/live_camera_panel.dart',
                         'test/production_phase4_test.dart')]
result={'phase':4,'completed_at':datetime.now().astimezone().isoformat(),'WEB_API_INTEGRATION_OFFLINE_READY':'YES',
        'phase5_started':False,'staging_bundle_created':False,'physical_pass':False,
        'production_runtime_changed':False,'production_db_changed':False,'camera_opened':False,'serial_opened':False,
        'servo':'LOCKED','pump':'LOCKED','backend_tests_passed':python_count,'flutter_tests_passed':flutter_count,
        'flutter_tests_skipped':0,'flutter_analyze':'PASS_NO_ISSUES','web_builds':{m:build[m] for m in ('real','mock')},
        'frontend_secret_sentinel_absent':build['producer_secret_sentinel_absent'],
        'api_fixture_sha256':sha(OUT/'api_contract_fixture.json'),
        'source_sha256':{str(p):sha(p) for p in files},
        'evidence_sha256':{name:sha(OUT/name) for name in ('backend_focused.log','flutter_focused.log',
            'flutter_analyze.log','flutter_build_real.log','flutter_build_mock.log')}}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('completed_at','WEB_API_INTEGRATION_OFFLINE_READY','backend_tests_passed','flutter_tests_passed','phase5_started')}))
