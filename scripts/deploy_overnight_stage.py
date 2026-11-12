"""Apply only reviewed session files; preserve original staged index/user edits."""
import hashlib,json,pathlib,shutil
ROOT=pathlib.Path('/home/toan/for_cat')
STAGE=pathlib.Path('/tmp/for_cat_overnight_stage')
E=ROOT/'evidence/overnight_integration_20261023'
previous=json.loads((E/'audit.json').read_text())
assert hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==previous['git_index_sha256']
manifest=E/'session_files.json'
owned=json.loads(manifest.read_text()) if manifest.exists() else {}
for src in sorted(STAGE.rglob('*')):
    if not src.is_file():continue
    relative=str(src.relative_to(STAGE))
    dst=ROOT/relative
    if dst.exists():
        original=E/'originals'/relative
        old=hashlib.sha256(dst.read_bytes()).hexdigest()
        assert (relative in owned and old==owned[relative]) or (original.is_file() and dst.read_bytes()==original.read_bytes()),relative
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(str(src),str(dst))
    owned[relative]=hashlib.sha256(dst.read_bytes()).hexdigest()
manifest.write_text(json.dumps(owned,indent=2,sort_keys=True))
print('DEPLOYED',len(owned),'session files; original git index preserved')
