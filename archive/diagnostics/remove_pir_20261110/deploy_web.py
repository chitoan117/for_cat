import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import urllib.request

EVIDENCE = Path(__file__).resolve().parent
PARENT = Path('/home/toan/for_cat/.native-build/flutter')
LIVE = PARENT / 'four_ultrasonic_20261027_r2'
STAGE = PARENT / 'four_ultrasonic_20261027_r2.remove_pir_20261110_staged'
BACKUP = PARENT / 'four_ultrasonic_20261027_r2.before_remove_pir_20261110'
UNITS = ['for-cat-api.service', 'for-cat-esp32-bridge.service', 'for-cat-ai.service']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def services():
    result = {}
    for unit in UNITS:
        result[unit] = subprocess.check_output(
            ['systemctl', '--user', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState'],
            universal_newlines=True).strip()
        if 'ActiveState=active' not in result[unit]:
            raise RuntimeError('Service not active: ' + unit)
    return result

def get(url):
    req = urllib.request.Request('http://127.0.0.1:8000' + url,
                                 headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=20) as response:
        assert response.status == 200
        return response.read()

assert PARENT.resolve() == PARENT and LIVE.resolve() == LIVE and LIVE.is_dir()
assert LIVE.stat().st_uid == os.getuid()
assert not BACKUP.exists() and not STAGE.exists(), 'Release or backup directory already exists'
manifest = json.loads((EVIDENCE / 'web_manifest.json').read_text())
archive = EVIDENCE / 'remove_pir_20261110.tar.gz'
assert sha(archive) == manifest['bundle_sha256'], 'Archive checksum mismatch'
assert sha(LIVE / 'main.dart.js') == manifest['expected_previous_main_sha256'], 'Live build changed since review'
before_services = services()
before_status = json.loads(get('/api/status').decode())
STAGE.mkdir(mode=0o755)
seen = set()
with tarfile.open(str(archive), 'r:gz') as bundle:
    for member in bundle:
        name = member.name
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and name in manifest['files']
        assert member.isfile() and name not in seen, 'Unexpected entry: ' + name
        seen.add(name)
        dest = STAGE.joinpath(*path.parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with bundle.extractfile(member) as src, dest.open('wb') as out:
            shutil.copyfileobj(src, out)
        dest.chmod(0o644)
        assert sha(dest) == manifest['files'][name], 'File checksum mismatch: ' + name
assert seen == set(manifest['files'])
marker = json.loads((STAGE / 'forcat_build.json').read_text(encoding='utf-8-sig'))
assert marker['mode'] == 'REAL' and marker['base_href'] == '/flutter/' and marker['target_grams'] == 35
assert '<base href="/flutter/">' in (STAGE / 'index.html').read_text()
assert (STAGE / 'canvaskit/canvaskit.wasm').is_file()

LIVE.rename(BACKUP)
try:
    STAGE.rename(LIVE)
    assert b'<base href="/flutter/">' in get('/app')
    assert hashlib.sha256(get('/flutter/main.dart.js')).hexdigest() == manifest['files']['main.dart.js']
    checked = {}
    for asset in ['flutter_bootstrap.js', 'assets/FontManifest.json',
                  'assets/assets/fonts/Roboto-Regular.ttf', 'canvaskit/canvaskit.js',
                  'canvaskit/canvaskit.wasm', 'forcat_build.json']:
        data = get('/flutter/' + asset)
        assert hashlib.sha256(data).hexdigest() == manifest['files'][asset]
        checked[asset] = len(data)
    after_services = services()
    assert before_services == after_services, 'Unexpected service restart'
    after_status = json.loads(get('/api/status').decode())
except Exception:
    if LIVE.exists():
        LIVE.rename(PARENT / 'four_ultrasonic_20261027_r2.remove_pir_20261110_failed')
    BACKUP.rename(LIVE)
    raise

result = {
    'release': manifest['release'], 'status': 'deployed',
    'live': str(LIVE), 'backup': str(BACKUP),
    'main_sha256': manifest['files']['main.dart.js'],
    'services_unchanged': after_services, 'asset_http_checks': checked,
    'api_status_available_before_and_after': True,
    'hardware_commands_sent_by_deployment': 0,
}
(EVIDENCE / 'deployment_result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
