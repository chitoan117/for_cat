import hashlib
import json
import tarfile
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web_real'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

marker = json.loads((WEB / 'forcat_build.json').read_text(encoding='utf-8-sig'))
assert marker['mode'] == 'REAL' and marker['target_grams'] == 35
assert marker['base_href'] == '/flutter/'
assert '<base href="/flutter/">' in (WEB / 'index.html').read_text(encoding='utf-8')
assert (WEB / 'assets/assets/fonts/Roboto-Regular.ttf').is_file()
assert (WEB / 'canvaskit/canvaskit.wasm').is_file()
# Content-addressed entry points make an ordinary refresh load this release
# even when an older Flutter service worker has cached the unversioned files.
release_hash = sha(WEB / 'main.dart.js')[:12]
entry = 'main.' + release_hash + '.dart.js'
asset_base = 'release.' + release_hash
shutil.copytree(WEB / 'assets', WEB / asset_base / 'assets', dirs_exist_ok=True)
bootstrap = (WEB / 'flutter_bootstrap.js').read_text(encoding='utf-8')
assert '"mainJsPath":"main.dart.js"' in bootstrap
bootstrap = bootstrap.replace('"mainJsPath":"main.dart.js"', '"mainJsPath":"' + entry + '"')
bootstrap = bootstrap.replace('_flutter.loader.load({', '_flutter.loader.load({\n  config: {assetBase: "/flutter/' + asset_base + '/"},')
bootstrap = bootstrap.replace('_flutter.loader.load();', '_flutter.loader.load({config: {assetBase: "/flutter/' + asset_base + '/"}});')
bootstrap_name = 'flutter_bootstrap.' + hashlib.sha256(bootstrap.encode()).hexdigest()[:12] + '.js'
(WEB / bootstrap_name).write_text(bootstrap, encoding='utf-8')
shutil.copy2(WEB / 'main.dart.js', WEB / entry)
index = (WEB / 'index.html').read_text(encoding='utf-8')
index = re.sub(r'src="flutter_bootstrap(?:\.[a-f0-9]+)?\.js"', 'src="' + bootstrap_name + '"', index)
(WEB / 'index.html').write_text(index, encoding='utf-8')
files = {p.relative_to(WEB).as_posix(): sha(p) for p in sorted(WEB.rglob('*')) if p.is_file()}
archive = ROOT / 'remove_pir_20261110.tar.gz'
with tarfile.open(archive, 'w:gz') as out:
    for name in files:
        out.add(str(WEB / name), arcname=name, recursive=False)
manifest = {
    'release': 'remove_pir_20261110',
    'entry_point': entry,
    'bootstrap': bootstrap_name,
    'asset_base': asset_base,
    'bundle_sha256': sha(archive),
    'expected_previous_main_sha256': 'fd0b66accb677af921834fcf53b823fec6cf313781ed980bdb563478df5dc0a0',
    'files': files,
}
(ROOT / 'web_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'files': len(files), 'bundle_bytes': archive.stat().st_size,
                  'main_sha256': files['main.dart.js'], 'bundle_sha256': manifest['bundle_sha256']}, indent=2))
