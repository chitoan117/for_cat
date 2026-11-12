"""Evidence-only finalization; no test reruns, camera, network or deployment."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;FE=Path(r'D:\DA_KT_NC\feeder_demo')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
e2e=json.loads((ROOT/'E2E_OFFLINE_DEMO_20261028/latest_run.json').read_text(encoding='utf-8'))['result']
assert e2e['E2E_OFFLINE_DEMO_READY'] is True
for name,digest in e2e['production_sources_unchanged_sha256'].items():assert sha(ROOT/name)==digest,name
old=json.loads((ROOT/'WEB_FINAL_20261027/result.json').read_text(encoding='utf-8'))
for mode in ('real','mock'):
    assert sha(ROOT/'WEB_FINAL_20261027'/('web_'+mode)/'main.dart.js')==old['build_'+mode]['main_dart_js_sha256']
backend=(OUT/'backend_focused.log').read_text(encoding='utf-8');assert '32 passed' in backend and 'failed' not in backend.lower()
native=(OUT/'preview_test.log').read_text(encoding='utf-8');assert 'PREVIEW_QUEUE_PASS' in native
browser=json.loads((OUT/'browser_result.json').read_text(encoding='utf-8'))
http=json.loads((OUT/'windows_http_result.json').read_text(encoding='utf-8'))
assert browser['status']==http['status']=='PASS'
assert browser['observed_classes']==['CAT','DOG','NONE'] and not browser['external_requests'] and not browser['runtime_errors']
assert all(r['method']=='GET' for r in browser['requests'])
assert browser['final_status']['viewers']==0 and http['feed_side_effects'] is False
builds=json.loads((OUT/'flutter_build_result.json').read_text(encoding='utf-8'))
for mode,metadata in builds.items():assert sha(OUT/('web_'+mode)/'main.dart.js')==metadata['main_dart_js_sha256']
grants=json.loads((OUT/'tailscale-grants.example.json').read_text(encoding='utf-8'))
assert all(rule['ip']==['tcp:443'] for rule in grants['grants'])
assert 'funnel' not in (OUT/'serve_private.sh').read_text(encoding='utf-8').lower()
backend_names=['jetson/app/main.py','jetson/app/http_middleware.py','jetson/app/camera/live_stream.py','jetson/app/camera/remote_access.py',
               'jetson/tools/run_api.py','jetson/device/preview_queue.h','jetson/device/preview_publisher.h','jetson/device/roi_ai_source.cpp']
frontend_names=['lib/user_pages.dart','lib/live_camera_controller.dart','lib/live_camera_panel.dart','lib/live_camera_image.dart',
                'lib/live_camera_image_stub.dart','lib/live_camera_image_web.dart','test/live_camera_test.dart']
result={'generated_utc':datetime.now(timezone.utc).isoformat(),'LIVE_CAMERA_OFFLINE_READY':True,
        'backend_focused_tests':32,'cpp14_preview_queue_assertions':20015,
        'flutter_camera_tests':{'passed':6,'provenance':'Actual flutter test tool run in this milestone; not rerun just to archive output'},
        'flutter_related_overview_tests':{'passed':24,'provenance':'Affected overview/user_app_offline suite run earlier in this milestone; no full regression'},
        'flutter_analyze':'PASS_NO_ISSUES_TOOL_RUN','flutter_real_mock_builds':builds,
        'windows_actual_http':'PASS','chrome_actual_mjpeg':'PASS','observed_classes':['CAT','DOG','NONE'],
        'same_origin_only':True,'tailnet_access':'PREPARED_NOT_EXECUTED','camera_physical':'NOT_VERIFIED',
        'arm64_cuda_tensorrt_updated_build':'NOT_VERIFIED','e2e_core_hashes_preserved':True,'web_final_artifacts_preserved':True,
        'servo':'LOCKED','pump':'LOCKED','hx711':'PHYSICAL_VALIDATION_PENDING',
        'backend_source_sha256':{name:sha(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'/name) for name in backend_names},
        'frontend_source_sha256':{name:sha(FE/name) for name in frontend_names},
        'evidence_sha256':{p.name:sha(p) for p in [OUT/'backend_focused.log',OUT/'preview_compile.log',OUT/'preview_test.log',OUT/'windows_http_result.json',OUT/'browser_result.json',
          OUT/'flutter_simulated_live.png',OUT/'flutter_simulated_roi_dog.png',OUT/'flutter_simulated_none.png']}}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if not k.endswith('sha256')},indent=2))
