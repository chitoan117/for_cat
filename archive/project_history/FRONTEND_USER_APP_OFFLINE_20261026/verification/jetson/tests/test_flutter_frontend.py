import json

from fastapi.testclient import TestClient
import pytest

from app.main import create_app


def artifact(tmp_path):
    root = tmp_path / 'flutter'; root.mkdir()
    (root / 'index.html').write_text('<base href="/flutter/"><title>SYNTHETIC_REAL_ARTIFACT_TEST</title>')
    (root / 'main.dart.js').write_text('// synthetic fixture, no hardware code')
    (root / 'flutter_bootstrap.js').write_text('// synthetic fixture')
    (root / 'canvaskit').mkdir()
    (root / 'forcat_build.json').write_text(json.dumps({'mode': 'REAL', 'base_href': '/flutter/', 'target_grams': 35}))
    return root


def test_both_views_serve_same_real_artifact_and_keep_existing_apis(tmp_path):
    root = artifact(tmp_path)
    with TestClient(create_app(db_path=tmp_path / 'state.db', flutter_web_dir=root)) as client:
        kiosk = client.get('/kiosk'); app = client.get('/app')
        assert kiosk.status_code == app.status_code == 200 and kiosk.content == app.content
        assert 'SYNTHETIC_REAL_ARTIFACT_TEST' in kiosk.text
        assert kiosk.headers['cache-control'] == 'no-store'
        assert client.get('/flutter/main.dart.js').status_code == 200
        assert client.get('/api/status').json()['data_source'] == 'REAL'
        assert client.get('/diagnostics').status_code == 200
        assert 'FOR_CAT' in client.get('/diagnostics').text


@pytest.mark.parametrize('mode,base,target', [('MOCK', '/flutter/', 35), ('REAL', '/', 35), ('REAL', '/flutter/', 40)])
def test_mock_wrong_prefix_or_target_artifact_fails_closed(tmp_path, mode, base, target):
    root = artifact(tmp_path)
    (root / 'forcat_build.json').write_text(json.dumps({'mode': mode, 'base_href': base, 'target_grams': target}))
    with pytest.raises(ValueError):
        create_app(db_path=tmp_path / 'not-opened.db', flutter_web_dir=root)
    assert not (tmp_path / 'not-opened.db').exists()


def test_static_assets_cannot_read_parent_files_and_incomplete_build_rejected(tmp_path):
    root = artifact(tmp_path); (tmp_path / 'secret.txt').write_text('synthetic private data')
    with TestClient(create_app(db_path=tmp_path / 'state.db', flutter_web_dir=root)) as client:
        response = client.get('/flutter/%2e%2e/secret.txt')
        assert response.status_code == 404 and 'synthetic private data' not in response.text
    (root / 'main.dart.js').unlink()
    with pytest.raises(ValueError):
        create_app(db_path=tmp_path / 'other.db', flutter_web_dir=root)
