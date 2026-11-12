"""R2 transfer/default-PLAN/output guards, temporary files only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verify_transfer import verify
from native_arm64_r2 import output_path

def fixture(root):
    p=root/'source.h';p.write_bytes(b'SIMULATED_SOURCE')
    manifest={'kind':'FORCAT_R2_SOURCE_DELTA','revision':'GCC75_R2','files':{'source.h':{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}}
    raw=json.dumps(manifest).encode();(root/'TRANSFER_MANIFEST.json').write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest();(root/'TRANSFER_MANIFEST.sha256').write_text(digest+'\n')
    return manifest,digest

def test_correct_transfer_is_readonly(tmp_path):
    _,digest=fixture(tmp_path);before={p.name:p.stat().st_mtime_ns for p in tmp_path.iterdir()}
    assert verify(tmp_path,digest,required=('source.h',))['transfer_integrity']=='PASS'
    assert before=={p.name:p.stat().st_mtime_ns for p in tmp_path.iterdir()}

@pytest.mark.parametrize('failure',['tamper','missing','manifest_hash','external_hash','wrong_revision','parent_traversal'])
def test_transfer_fail_closed(tmp_path,failure):
    m,digest=fixture(tmp_path)
    if failure=='tamper':(tmp_path/'source.h').write_bytes(b'OTHER_FILE_BYTES')
    if failure=='missing':(tmp_path/'source.h').unlink()
    if failure=='manifest_hash':(tmp_path/'TRANSFER_MANIFEST.sha256').write_text('0'*64)
    if failure=='external_hash':digest='0'*64
    if failure in ('wrong_revision','parent_traversal'):
        if failure=='wrong_revision':m['revision']='GCC75_R1'
        else:m['files']={'../source.h':m['files']['source.h']}
        raw=json.dumps(m).encode();(tmp_path/'TRANSFER_MANIFEST.json').write_bytes(raw)
        digest=hashlib.sha256(raw).hexdigest();(tmp_path/'TRANSFER_MANIFEST.sha256').write_text(digest)
    with pytest.raises(ValueError):verify(tmp_path,digest,required=('source.h',))

def test_manifest_must_cover_native_execution_inputs(tmp_path):
    _,digest=fixture(tmp_path)
    with pytest.raises(ValueError,match='required executable/test inputs'):verify(tmp_path,digest)

def test_output_cannot_use_R1_existing_or_outside_root(tmp_path):
    assert output_path(tmp_path/'native_arm64_r2_new',tmp_path)==tmp_path/'native_arm64_r2_new'
    (tmp_path/'native_arm64_r2_old').mkdir()
    for p in (tmp_path/'native_arm64_r2_old',tmp_path/'native_arm64_gcc75_r1',tmp_path.parent/'native_arm64_r2_bad'):
        with pytest.raises(ValueError):output_path(p,tmp_path)

def test_plan_does_not_create_output_or_execute_build(tmp_path):
    out=tmp_path/'native_arm64_r2_should_not_exist'
    p=subprocess.run([sys.executable,'-B',str(ROOT/'native_arm64_r2.py'),'--out',str(out)],capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
    value=json.loads(p.stdout);assert value['mode']=='PLAN_ONLY' and value['ARM64_NATIVE_TEST_PASS']=='NOT_RUN'
    assert value['serial_opened'] is False and not out.exists()

def test_windows_cannot_claim_arm64_acceptance(tmp_path):
    if sys.platform!='win32':pytest.skip('Windows host rejection check')
    out=tmp_path/'native_arm64_r2_should_not_exist'
    p=subprocess.run([sys.executable,'-B',str(ROOT/'native_arm64_r2.py'),'--execute','BUILD_AND_FILE_REPLAY_ONLY','--out',str(out)],capture_output=True,text=True,timeout=15)
    assert p.returncode!=0 and 'requires actual Linux ARM64' in p.stderr and not out.exists()
