"""Standalone read-only kit integrity check; no PlatformIO/device dependency."""
import sys
sys.dont_write_bytecode=True
import argparse
import json
from pathlib import Path
from image_layout import sha
def verify(root):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('kind')!='FORCAT_PHYSICAL_KIT_INTEGRITY_V1':raise ValueError('wrong kit manifest')
    if sha(root/'manifest.json')!=(root/'manifest.sha256').read_text().strip():raise ValueError('manifest digest mismatch')
    for name,meta in manifest['files'].items():
        parts=name.split('/')
        if name.startswith('/') or ':' in name or '\\' in name or any(s in ('','.','..') for s in parts):raise ValueError('unsafe manifest path')
        p=root/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:raise ValueError('kit file mismatch '+name)
    expected=''.join(meta['sha256']+'  '+name+'\n' for name,meta in sorted(manifest['files'].items()))
    if (root/'SHA256SUMS').read_text()!=expected:raise ValueError('SHA256SUMS mismatch')
    return {'software_integrity':'PASS','files_checked':len(manifest['files']),'manifest_sha256':sha(root/'manifest.json'),'physical_pass':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    print(json.dumps(verify(a.root),indent=2))
