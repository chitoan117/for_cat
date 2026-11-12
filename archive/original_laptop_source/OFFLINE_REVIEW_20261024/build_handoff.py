"""Package only the six reviewed Python source/test changes; no device access."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

OUT=Path(__file__).resolve().parent
PROJECT=OUT/'project'
BUNDLE=OUT/'handoff'
STAGE=Path(r'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_overnight_stage')
baseline=json.loads((OUT/'DEPLOYED_SOURCE_BASELINE.json').read_text(encoding='utf-8'))['files']
names=['jetson/app/device_state.py','jetson/app/ai_state.py','jetson/app/system_state.py',
       'jetson/tests/test_device_state_api.py','jetson/tests/test_system_state.py',
       'jetson/tests/test_state_cache_resilience.py']
assert BUNDLE.is_dir() and not (BUNDLE/'manifest.json').exists() and not (BUNDLE/'payload').exists()
records={};diff=[]
for name in names:
    source=PROJECT/name
    after=source.read_bytes()
    old=(STAGE/name).read_bytes() if name in baseline else b''
    if name in baseline:
        assert hashlib.sha256(old).hexdigest()==baseline[name]
    target=BUNDLE/'payload'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    records[name]={'before_sha256':baseline.get(name),'after_sha256':hashlib.sha256(after).hexdigest()}
    diff.extend(difflib.unified_diff(old.decode('utf-8').splitlines(keepends=True),after.decode('utf-8').splitlines(keepends=True),
                                    fromfile='a/'+name if old else '/dev/null',tofile='b/'+name))
(BUNDLE/'manifest.json').write_text(json.dumps({'schema_version':1,'scope':'BACKEND_CACHE_AVAILABILITY_ONLY',
    'source_head':'dff667d13ac0cff78a494ab33070c1e9cf583f3f','not_applied_to_jetson':True,
    'no_hardware_operations':True,'files':records},indent=2),encoding='utf-8')
(BUNDLE/'review.diff').write_text(''.join(diff),encoding='utf-8')
print('HANDOFF READY',BUNDLE,'files',len(records))
