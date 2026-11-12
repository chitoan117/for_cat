"""Trusted locked-R2 fixture, then a NONEXECUTED extra file; no malicious code runs."""
import hashlib,importlib.util,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'CANDIDATE_GCC75_R2_20261029'
spec=importlib.util.spec_from_file_location('baseline_verifier',ROOT/'baseline_tools/verify_transfer.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
archive=BASE/'R2_SOURCE_DELTA.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='64931aa7517541a09d41c38c5e60872e07379a4708895dc04a7b79770a754f79'
with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(archive) as z:z.extractall(tmp) # trusted fixed archive ONLY
    (Path(tmp)/'UNEXPECTED_SOURCE.py').write_text('NONEXECUTED_SYNTHETIC_TEXT')
    result=mod.verify(tmp,expected='3c9d7ffe1f1b32ab1fc22f7893f3902d0809001981e2e28823c995b43af4eb3c')
    result.update(unexpected_file_exists=True,baseline_gap='EXTRA_FILE_NOT_REJECTED',source='SYNTHETIC')
path=ROOT/'evidence/baseline_release.json'
with path.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
