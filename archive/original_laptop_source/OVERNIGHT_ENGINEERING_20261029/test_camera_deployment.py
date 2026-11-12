import json
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import camera_preflight as camera
import release_bundle as release

@pytest.fixture
def setup(tmp_path,monkeypatch):
    bundle=tmp_path/'release';web=bundle/'web_real';web.mkdir(parents=True)
    (web/'main.dart.js').write_text('FAKE_STATIC_TEST_ONLY')
    (web/'forcat_build.json').write_text(json.dumps({'mode':'REAL','base_href':'/flutter/','actuator_execution':False}))
    manifest={'kind':'FORCAT_OFFLINE_STAGING_V1','files':{}}
    for p in web.iterdir():manifest['files'][p.relative_to(bundle).as_posix()]={'bytes':p.stat().st_size,'sha256':release.digest(p)}
    (bundle/'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(camera,'WEB_SHA',release.digest(web/'main.dart.js'))
    private=tmp_path/'private';private.mkdir()
    token=private/'producer.token';token.write_text('TEST_ONLY_PRIVATE_TOKEN_0123456789abcdef')
    policy=private/'access.json';policy.write_text(json.dumps({'users':{'viewer@test.local':['VIEW_CAMERA'],'operator@test.local':['VIEW_CAMERA','FEED_MANUAL']}}))
    config={**camera.EXPECTED,'API_PORT':'8000','FORCAT_TAILSCALE_HOSTNAME':'forcat.tail123.ts.net',
            'FORCAT_CAMERA_PRODUCER_TOKEN_FILE':str(token),'FORCAT_ACCESS_POLICY_FILE':str(policy)}
    path=private/'server-env.json'
    def save():
        path.write_text(json.dumps(config))
        for p in (path,token,policy):os.chmod(p,0o600)
    save()
    return bundle,path,config,save
def test_safe_profile_without_operations(setup):
    b,p,_,_=setup;result=camera.validate(p,b)
    assert result['config_valid'] and result['providers_preserved'] and not result['camera_opened']
    assert result['real_stream']=='NOT_VERIFIED' and not result['network_changed']
@pytest.mark.parametrize('key,value',[('API_HOST','0.0.0.0'),('CAMERA_PROVIDER','REAL'),('AI_RUNTIME','REAL'),
    ('ESP32_TRANSPORT','REAL'),('SYSTEM_STATE_PROVIDER','MOCK'),('CORS_ORIGINS','*'),('FORCAT_REMOTE_MODE','DISABLED'),
    ('FORCAT_STREAM_SOURCE','MOCK'),('SCHEDULED_DRY_RUN_WORKER_ENABLED','1'),('API_PORT','80'),
    ('FORCAT_TAILSCALE_HOSTNAME','https://host.ts.net'),('FORCAT_TAILSCALE_HOSTNAME','*.ts.net'),
    ('FORCAT_TAILSCALE_HOSTNAME','host.ts.net:443'),('FORCAT_TAILSCALE_HOSTNAME','bad/host.ts.net')])
def test_unsafe_profile_rejected(setup,key,value):
    b,p,c,save=setup;c[key]=value;save()
    with pytest.raises(ValueError):camera.validate(p,b)
def test_viewer_cannot_be_same_privileged_role(setup):
    b,p,c,_=setup;policy=Path(c['FORCAT_ACCESS_POLICY_FILE'])
    policy.write_text(json.dumps({'users':{'only@test.local':['VIEW_CAMERA','FEED_MANUAL']}}))
    with pytest.raises(ValueError,match='separate'):camera.validate(p,b)
def test_missing_token_rejected(setup):
    b,p,c,save=setup;c['FORCAT_CAMERA_PRODUCER_TOKEN_FILE']=str(p.parent/'missing.token');save()
    with pytest.raises(ValueError):camera.validate(p,b)
def test_secret_inside_release_rejected(setup):
    b,p,c,save=setup;c['FORCAT_CAMERA_PRODUCER_TOKEN_FILE']=str(b/'web_real/main.dart.js');save()
    with pytest.raises(ValueError,match='outside'):camera.validate(p,b)
def test_tampered_web_rejected(setup):
    b,p,_,_=setup;(b/'web_real/main.dart.js').write_text('tampered')
    with pytest.raises(ValueError,match='integrity'):camera.validate(p,b)
def test_output_does_not_include_secret(setup):
    b,p,c,_=setup;result=json.dumps(camera.validate(p,b))
    assert Path(c['FORCAT_CAMERA_PRODUCER_TOKEN_FILE']).read_text() not in result
    assert c['FORCAT_ACCESS_POLICY_FILE'] not in result
