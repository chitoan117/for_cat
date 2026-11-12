import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

EVIDENCE = Path(__file__).resolve().parent
LIVE = Path('/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2')
manifest = json.loads((EVIDENCE / 'web_manifest.json').read_text())
archive = EVIDENCE / 'web_cleanup_20261106.tar.gz'
def digest(data):
    return hashlib.sha256(data).hexdigest()
assert LIVE.resolve() == LIVE and LIVE.stat().st_uid == os.getuid()
assert digest(archive.read_bytes()) == manifest['bundle_sha256']
assert digest((LIVE / 'main.dart.js').read_bytes()) == manifest['files']['main.dart.js']
names = [manifest['entry_point'], manifest['bootstrap'], 'index.html']
names = [name for name in manifest['files'] if name.startswith(manifest['asset_base'] + '/')] + names
old_index = (LIVE / 'index.html').read_bytes()
(EVIDENCE / 'index.before_cache_fix.html').write_bytes(old_index)
with tarfile.open(str(archive), 'r:gz') as bundle:
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and name in manifest['files']
        member = bundle.getmember(name)
        assert member.isfile()
        data = bundle.extractfile(member).read()
        assert digest(data) == manifest['files'][name]
        temporary = LIVE / (name + '.new')
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(data)
        temporary.chmod(0o644)
        temporary.replace(LIVE / name)

try:
    for name, expected in manifest['files'].items():
        assert digest((LIVE / name).read_bytes()) == expected, name
    for name in names:
        url = '/app' if name == 'index.html' else '/flutter/' + name
        with urllib.request.urlopen('http://127.0.0.1:8000' + url, timeout=20) as response:
            assert response.status == 200
            assert digest(response.read()) == manifest['files'][name]
except Exception:
    (LIVE / 'index.html').write_bytes(old_index)
    raise
result_path = EVIDENCE / 'deployment_result.json'
result = json.loads(result_path.read_text())
result['entry_point'] = manifest['entry_point']
result['bootstrap'] = manifest['bootstrap']
result['asset_base'] = manifest['asset_base']
result['versioned_entry_http_checks'] = True
result['all_deployed_file_hashes_match'] = True
result_path.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'versioned_entry_http_checks': True, 'entry_point': manifest['entry_point'],
                  'all_deployed_file_hashes_match': True}, indent=2))
