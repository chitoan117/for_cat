import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = Path('D:/DA_KT_NC/feeder_demo')
ALLOWED_LIB = {
    'user_pages.dart', 'ui_widgets.dart', 'status_model.dart', 'main.dart',
    'diagnostics_page.dart', 'meal_plan_panel.dart', 'live_camera_panel.dart',
}
ALLOWED_TEST = {
    'feeder_demo_test.dart', 'user_app_offline_test.dart', 'scheduled_worker_test.dart',
    'live_camera_test.dart', 'hx711_state_test.dart',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

changes = []
unchanged = []
for folder, allowed in [('lib', ALLOWED_LIB), ('test', ALLOWED_TEST)]:
    for updated in sorted((ROOT / 'app' / folder).rglob('*.dart')):
        rel = updated.relative_to(ROOT / 'app')
        before = ROOT / 'before' / rel
        assert before.is_file(), 'Unexpected new source file: ' + str(rel)
        if sha(updated) == sha(before):
            unchanged.append(str(rel))
            continue
        assert updated.name in allowed, 'Unexpected change: ' + str(rel)
        actual = SOURCE / rel
        assert sha(actual) == sha(before), 'Original changed during editing: ' + str(rel)
        changes.append((rel, updated, actual, sha(before), sha(updated)))
# Validate every file before changing any original source.
for rel, updated, actual, old_hash, new_hash in changes:
    shutil.copy2(updated, actual)
    assert sha(actual) == new_hash
result = {'source': str(SOURCE), 'changed': [
    {'file': str(rel), 'before_sha256': old_hash, 'after_sha256': new_hash}
    for rel, updated, actual, old_hash, new_hash in changes
], 'other_dart_files_unchanged': unchanged}
(ROOT / 'source_sync.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'source': str(SOURCE), 'updated': [str(item[0]) for item in changes],
                  'unchanged_dart_files': len(unchanged)}, indent=2))
