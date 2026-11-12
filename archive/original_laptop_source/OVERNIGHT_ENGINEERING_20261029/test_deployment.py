import json
from pathlib import Path
import shutil
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import release_bundle as release
import stage_release as stage
import jetson_build as build
import jetson_preflight as preflight

@pytest.fixture
def bundle(tmp_path):
    b=tmp_path/'inbox/release_A';b.mkdir(parents=True)
    (b/'source.cpp').write_text('int main(){}',encoding='utf-8')
    m={'kind':'FORCAT_OFFLINE_STAGING_V1','files':{'source.cpp':{'bytes':12,'sha256':release.digest(b/'source.cpp')}},'arm64_build':'NOT_VERIFIED'}
    (b/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
    return b

def test_manifest_verifies(bundle):assert release.verify(bundle)['arm64_build']=='NOT_VERIFIED'
@pytest.mark.parametrize('name',['../outside','/etc/shadow','a/../../b','C:/x','a\\b','./a','a//b'])
def test_path_escape_rejected(bundle,name):
    m=json.loads((bundle/'manifest.json').read_text());m['files']={name:{'bytes':0,'sha256':''}}
    (bundle/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):release.verify(bundle)
def test_changed_content_rejected(bundle):
    (bundle/'source.cpp').write_text('bad content!')
    with pytest.raises(ValueError,match='integrity'):release.verify(bundle)
def test_extra_secret_rejected(bundle):
    (bundle/'producer.token').write_text('private')
    with pytest.raises(ValueError,match='unexpected'):release.verify(bundle)
def test_source_collection_excludes_runtime():
    files=release.collect()
    assert files and 'payload/jetson/device/roi_ai_source.cpp' in files
    assert 'tools/release_bundle.py' in files
    assert all(not any(part in release.BLOCKED for part in Path(name).parts) for name in files)
    assert all(not name.endswith(('.db','.engine','.env','.token')) for name in files)
    assert all(not name.endswith('.bin') or name.startswith('web_real/') for name in files)
def test_stage_default_is_plan(bundle,tmp_path):
    result=stage.stage(bundle,tmp_path/'stage',tmp_path/'production')
    assert result['plan_only'] and not (tmp_path/'stage').exists()
def test_stage_copy_and_no_overwrite(bundle,tmp_path):
    prod=tmp_path/'production';prod.mkdir();(prod/'sentinel').write_text('preserved')
    result=stage.stage(bundle,tmp_path/'stage',prod,True)
    assert release.verify(result['target']) and (prod/'sentinel').read_text()=='preserved'
    with pytest.raises(ValueError):stage.stage(bundle,tmp_path/'stage',prod,True)
@pytest.mark.parametrize('subpath',['production','production/staging','.'])
def test_staging_must_be_disjoint(bundle,tmp_path,subpath):
    with pytest.raises(ValueError,match='disjoint'):stage.stage(bundle,tmp_path/subpath,tmp_path/'production')
def test_build_plan_no_execution(bundle,tmp_path):
    # Stage first; only build paths outside the immutable tree are accepted.
    result=stage.stage(bundle,tmp_path/'stage',tmp_path/'production',True)
    b=Path(result['target']);out=tmp_path/'stage/build/release_A/run1'
    assert build.build_plan(b,out)[0]==out
    assert not out.exists()
    with pytest.raises(ValueError):build.build_plan(b,b/'build/run1')
def test_readonly_preflight_never_invokes_device_or_write(monkeypatch,tmp_path):
    commands=[]
    monkeypatch.setattr(preflight,'query',lambda q:commands.append(q) or {'returncode':1,'argv':q})
    result=preflight.inspect(tmp_path)
    assert not result['build_preconditions'] and not result['camera_opened']
    assert all(q[0] in ('g++','pkg-config','systemctl','fuser','v4l2-ctl') for q in commands)
    assert all(q[1]=='is-active' for q in commands if q[0]=='systemctl')
def test_rollback_missing_previous_rejected(tmp_path):
    backup=tmp_path/'selection_backup_test.json';backup.write_text('{"previous":null}')
    with pytest.raises(ValueError,match='no previous'):stage.rollback(tmp_path,backup)
def test_select_outside_staging_rejected(bundle,tmp_path):
    with pytest.raises(ValueError,match='outside'):stage.select(tmp_path/'stage',bundle)
