"""Temporary Git repositories only; no real checkout/hardware/SSH, no commits."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

OUT=Path(__file__).resolve().parent
BUNDLE=OUT/'handoff'
STAGE=Path(r'C:\Users\chito\AppData\Local\Temp\opencode\for_cat_overnight_stage')
spec=importlib.util.spec_from_file_location('source_updater',BUNDLE/'apply_source_update.py')
updater=importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def run_git(root,*args):
    return subprocess.run(['git',*args],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout


@pytest.fixture
def repo(tmp_path):
    root=tmp_path/'project';root.mkdir()
    manifest=json.loads((BUNDLE/'manifest.json').read_text())
    for name,record in manifest['files'].items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        if record['before_sha256'] is not None:
            shutil.copy2(STAGE/name,path)
    (root/'jetson/app/main.py').write_text('# synthetic entrypoint marker\n')
    (root/'docs').mkdir()
    (root/'docs/user_notes.txt').write_text('original staged user work\n')
    run_git(root,'init')
    run_git(root,'add','jetson','docs')
    return root


def test_check_is_read_only_and_apply_preserves_index_and_is_idempotent(repo):
    before=updater.sha(repo/'.git/index')
    result=updater.apply_updates(repo,BUNDLE)
    assert set(result['files'].values())=={'READY'}
    assert not (repo/'evidence').exists() and updater.sha(repo/'.git/index')==before
    applied=updater.apply_updates(repo,BUNDLE,apply=True)
    assert len(applied['applied_files'])==6
    assert updater.sha(repo/'.git/index')==before
    assert (repo/'docs/user_notes.txt').read_text()=='original staged user work\n'
    again=updater.apply_updates(repo,BUNDLE,apply=True)
    assert set(again['files'].values())=={'ALREADY_APPLIED'}
    assert len(list((repo/'evidence').iterdir()))==1


def test_source_conflict_aborts_before_any_write(repo):
    path=repo/'jetson/app/ai_state.py'
    path.write_text('# user edited this source\n')
    before=updater.sha(repo/'jetson/app/device_state.py')
    with pytest.raises(RuntimeError,match='source conflict'):
        updater.apply_updates(repo,BUNDLE,apply=True)
    assert updater.sha(repo/'jetson/app/device_state.py')==before
    assert path.read_text()=='# user edited this source\n'
    assert not (repo/'evidence').exists()


def test_corrupt_payload_aborts(repo,tmp_path):
    bad=tmp_path/'bad_bundle';shutil.copytree(BUNDLE,bad)
    (bad/'payload/jetson/app/device_state.py').write_text('# corrupted transfer\n')
    with pytest.raises(RuntimeError,match='payload checksum mismatch'):
        updater.apply_updates(repo,bad,apply=True)
    assert not (repo/'evidence').exists()


def test_injected_write_failure_rolls_back_only_owned_changes(repo):
    manifest=json.loads((BUNDLE/'manifest.json').read_text())
    before=updater.sha(repo/'.git/index')
    count=0
    def failing_writer(path,data,mode):
        nonlocal count
        count+=1
        if count==2:
            raise OSError('synthetic write failure')
        updater.atomic_write(path,data,mode)
    with pytest.raises(OSError):
        updater.apply_updates(repo,BUNDLE,apply=True,writer=failing_writer)
    for name,record in manifest['files'].items():
        assert updater.sha(repo/name)==record['before_sha256']
    assert updater.sha(repo/'.git/index')==before


def test_concurrent_git_stage_is_not_overwritten(repo):
    initial=updater.sha(repo/'.git/index')
    staged_after=None
    changed=False
    def concurrent_writer(path,data,mode):
        nonlocal changed,staged_after
        updater.atomic_write(path,data,mode)
        if not changed:
            changed=True
            (repo/'docs/user_notes.txt').write_text('new user work staged during update\n')
            run_git(repo,'add','docs/user_notes.txt')
            staged_after=updater.sha(repo/'.git/index')
    with pytest.raises(RuntimeError,match='Git index changed concurrently'):
        updater.apply_updates(repo,BUNDLE,apply=True,writer=concurrent_writer)
    assert staged_after!=initial and updater.sha(repo/'.git/index')==staged_after
    assert run_git(repo,'show',':docs/user_notes.txt')==b'new user work staged during update\n'


def test_manifest_scope_cannot_target_firmware_or_model(repo,tmp_path):
    bad=tmp_path/'bad_scope';shutil.copytree(BUNDLE,bad)
    manifest=json.loads((bad/'manifest.json').read_text())
    manifest['files']['esp32/src/diagnostics.cpp']={'before_sha256':None,'after_sha256':'0'*64}
    (bad/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError,match='unexpected update scope'):
        updater.apply_updates(repo,bad,apply=True)
    assert not (repo/'evidence').exists()


def test_source_edit_between_preflight_and_write_is_preserved(repo):
    second=repo/'jetson/app/ai_state.py'
    count=0
    def writer_with_user_edit(path,data,mode):
        nonlocal count
        updater.atomic_write(path,data,mode)
        count+=1
        if count==1:
            second.write_text('# concurrent user source\n')
    with pytest.raises(RuntimeError,match='source changed concurrently'):
        updater.apply_updates(repo,BUNDLE,apply=True,writer=writer_with_user_edit)
    assert second.read_text()=='# concurrent user source\n'
    baseline=json.loads((BUNDLE/'manifest.json').read_text())['files']
    assert updater.sha(repo/'jetson/app/device_state.py')==baseline['jetson/app/device_state.py']['before_sha256']


def test_concurrent_edit_of_updated_file_is_not_clobbered_by_rollback(repo):
    first=repo/'jetson/app/device_state.py'
    count=0
    def writer_with_later_user_edit(path,data,mode):
        nonlocal count
        count+=1
        if count==2:
            first.write_text('# user changed the just-updated file\n')
            raise OSError('synthetic second write failure')
        updater.atomic_write(path,data,mode)
    with pytest.raises(OSError):
        updater.apply_updates(repo,BUNDLE,apply=True,writer=writer_with_later_user_edit)
    assert first.read_text()=='# user changed the just-updated file\n'
    failure=next((repo/'evidence').glob('*/failed.json'))
    assert json.loads(failure.read_text())['concurrent_edits_preserved']==['jetson/app/device_state.py']
