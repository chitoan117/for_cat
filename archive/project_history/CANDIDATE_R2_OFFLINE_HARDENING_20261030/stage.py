"""Snapshot locked R2 and read-only application sources into a new workspace."""
import hashlib,json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent;WS=ROOT.parent;BASE=WS/'CANDIDATE_GCC75_R2_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (ROOT/'candidate').exists():raise ValueError('hardening candidate exists; no overwrite')
    assert sha(BASE/'TRANSFER_MANIFEST.json')=='3c9d7ffe1f1b32ab1fc22f7893f3902d0809001981e2e28823c995b43af4eb3c'
    inputs={}
    def take(p,rel):
        q=ROOT/rel;q.parent.mkdir(parents=True,exist_ok=True)
        with q.open('xb') as f:f.write(p.read_bytes())
        inputs[rel]={'source':str(p),'sha256':sha(p)}
    m=json.loads((BASE/'TRANSFER_MANIFEST.json').read_text())
    for name,meta in m['files'].items():
        p=BASE/name;assert sha(p)==meta['sha256'],name
        if name.startswith(('candidate/','fixtures/')) and not name.endswith('test/continuation_test.dart'):take(p,name)
    app=WS/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app'
    for p in sorted(app.rglob('*.py')):take(p,'candidate/backend/app/'+p.relative_to(app).as_posix())
    config=app.parents[0]/'config/hardware_current.json'
    if config.is_file():take(config,'candidate/backend/config/hardware_current.json')
    for name in ('native_checks.py','native_arm64_r2.py','verify_transfer.py'):take(BASE/name,'baseline_tools/'+name)
    for name in ('evidence','tests','tools'):(ROOT/name).mkdir(exist_ok=True)
    (ROOT/'BASELINE_INPUTS.json').write_text(json.dumps({'base':'GCC75_R2','R2_manifest_sha256':sha(BASE/'TRANSFER_MANIFEST.json'),
        'R2_zip_sha256':sha(BASE/'R2_SOURCE_DELTA.zip'),'inputs':inputs},indent=2)+'\n')
    print(json.dumps({'sources_copied':len(inputs),'locked_R2_changed':False}))
if __name__=='__main__':main()
