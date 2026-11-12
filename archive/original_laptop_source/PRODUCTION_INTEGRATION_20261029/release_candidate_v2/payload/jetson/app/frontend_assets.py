"""Validate an explicit REAL Flutter artifact; never silently load a demo build."""
import json
from pathlib import Path


def resolve_flutter_frontend(value):
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    for name in ('index.html', 'main.dart.js', 'flutter_bootstrap.js', 'forcat_build.json'):
        if not (root / name).is_file():
            raise ValueError('Flutter artifact incomplete: ' + name)
    marker = root / 'forcat_build.json'
    if marker.stat().st_size > 65536:
        raise ValueError('Flutter build marker too large')
    metadata = json.loads(marker.read_text(encoding='utf-8'))
    if not isinstance(metadata, dict) or metadata.get('mode') != 'REAL' or metadata.get('base_href') != '/flutter/' or metadata.get('target_grams') != 35:
        raise ValueError('Only the reviewed REAL /flutter/ artifact may be served')
    index = (root / 'index.html').read_text(encoding='utf-8')
    if '<base href="/flutter/">' not in index or not (root / 'canvaskit').is_dir():
        raise ValueError('Flutter requires local assets and /flutter/ base href')
    return root
