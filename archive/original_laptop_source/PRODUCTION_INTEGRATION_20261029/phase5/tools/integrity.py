"""Immutable RC v2 integrity, path and backup receipts. No device operations."""
import hashlib
import json
from pathlib import Path, PurePosixPath

KIND='FORCAT_PRODUCTION_RC_V2'
def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):digest.update(chunk)
    return digest.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def safe(name):
    return isinstance(name,str) and bool(name) and not PurePosixPath(name).is_absolute() and '\\' not in name and ':' not in name and all(p not in ('','.','..') for p in name.split('/'))
def verify(root):
    root=Path(root)
    if root.is_symlink():raise ValueError('release root symlink')
    manifest=read(root/'manifest.json')
    if manifest.get('kind')!=KIND or not manifest.get('files'):raise ValueError('wrong/empty release manifest')
    if (root/'manifest.sha256').read_text().strip()!=sha(root/'manifest.json'):raise ValueError('manifest hash mismatch')
    for name,meta in manifest['files'].items():
        if not safe(name):raise ValueError('unsafe manifest path')
        p=root/name
        if not p.is_file() or p.is_symlink() or any(q.is_symlink() for q in p.parents):raise ValueError('missing/symlink '+name)
        if p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:raise ValueError('integrity mismatch '+name)
    paths=list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):raise ValueError('release symlink')
    actual={p.relative_to(root).as_posix() for p in paths if p.is_file()}
    if actual!=set(manifest['files'])|{'manifest.json','manifest.sha256','SHA256SUMS'}:raise ValueError('unmanifested files; use python -B')
    sums=''.join(meta['sha256']+'  '+name+'\n' for name,meta in sorted(manifest['files'].items()))
    if (root/'SHA256SUMS').read_text()!=sums:raise ValueError('SHA256SUMS mismatch')
    return manifest
def absolute(value):
    # Conservative systemd-safe path contract. No shell interpolation, specs or
    # whitespace in deployment paths; source path metadata may remain Windows.
    import re
    if not isinstance(value,str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+',value) or '..' in value.split('/'):
        raise ValueError('absolute systemd-safe Linux path required')
    return Path(value)
def verify_backup(path):
    path=Path(path);data=read(path/'backup.json')
    if data.get('kind')!='FORCAT_BACKUP_V2':raise ValueError('wrong backup kind')
    if (path/'backup.sha256').read_text().strip()!=sha(path/'backup.json'):raise ValueError('backup receipt mismatch')
    for name,digest in data['files'].items():
        if not safe(name) or sha(path/name)!=digest:raise ValueError('backup integrity mismatch')
    if data.get('database_integrity')!='ok':raise ValueError('backup DB integrity failed')
    return data
