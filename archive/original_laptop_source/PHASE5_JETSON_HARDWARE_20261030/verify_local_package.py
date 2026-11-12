"""Read/hash verification only; no Windows qualification suites or sealing."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

C = Path('D:/for_cat/CANDIDATE_R2_OFFLINE_HARDENING_20261030')
ZIP_SHA = '1c3b8abaf2586d91ac468c8c632d8750bf28a72d92f91130b983cb51dd99990d'
MANIFEST_SHA = 'a92fc2586daacaabb5e931f0b8603bb1a3bd159a1cd747f43fd8b0cff0a968d4'
archive = C / 'R2_HARDENING_SOURCE.zip'
raw = archive.read_bytes()
assert len(raw) == 288687 and hashlib.sha256(raw).hexdigest() == ZIP_SHA
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist()) == 147 and z.testzip() is None
    manifest_raw = z.read('SOURCE_MANIFEST.json')
    assert hashlib.sha256(manifest_raw).hexdigest() == MANIFEST_SHA
    manifest = json.loads(manifest_raw)
    assert len(manifest['files']) == 145
    for name, meta in manifest['files'].items():
        data = z.read(name)
        assert len(data) == meta['bytes'] and hashlib.sha256(data).hexdigest() == meta['sha256']
        assert (C / name).read_bytes() == data, name
sys.path.insert(0, str(C / 'tools'))
import safe_release
print(json.dumps({'zip_sha256': ZIP_SHA, 'zip_bytes': len(raw),
                  'archive': safe_release.archive(archive, MANIFEST_SHA),
                  'verifier_sha256': hashlib.sha256((C / 'tools/safe_release.py').read_bytes()).hexdigest(),
                  'native_runner_sha256': hashlib.sha256((C / 'tools/native_hardening.py').read_bytes()).hexdigest(),
                  'Windows_suites_rerun': 0}, indent=2))
