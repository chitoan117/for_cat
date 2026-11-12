"""Create a hash-pinned, source-only offline release; never modifies production.

Explicit source suffixes exclude databases, credentials, engines, binaries and
build caches. The existing detector is a reference build dependency, not a
replacement of /jetson/ai/cat_dog_trt. Nothing starts a process on Jetson.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PAYLOAD=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
SUFFIXES={'.py','.h','.hpp','.cpp','.sh','.txt','.json','.toml','.ini'}
BLOCKED={'__pycache__','.git','.pio','.venv','data','models','node_modules','build'}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def safe_name(name):
    p=PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '\\' not in name and ':' not in name and all(x not in ('','..','.') for x in name.split('/'))
def add_tree(files,source,prefix):
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if any(part in BLOCKED or part.startswith('.') for part in rel.parts):continue
        if p.is_symlink():raise ValueError('symlink source forbidden: '+str(p))
        if p.is_file() and p.suffix in SUFFIXES:
            # Environment/access policies are generated privately by the owner.
            if any(s in p.name.lower() for s in ('secret','token','.env','access.json')):continue
            files[prefix+'/'+rel.as_posix()]=p
def collect():
    files={}
    add_tree(files,PAYLOAD/'jetson/app','payload/jetson/app')
    add_tree(files,PAYLOAD/'jetson/device','payload/jetson/device')
    add_tree(files,PAYLOAD/'jetson/tools','payload/jetson/tools')
    add_tree(files,FW/'include','firmware_include')
    # Portable AI dependencies from the explicitly preserved detector reference.
    add_tree(files,ROOT/'OFFLINE_REVIEW_20261024/project/jetson/ai','ai_reference')
    for name in ('build_roi_ai_source.sh','build_esp32_bridge.sh','run_existing_ai.sh'):
        files['payload/scripts/'+name]=PAYLOAD/'scripts'/name
    for p in (PAYLOAD/'jetson').glob('requirements*.txt'):files['payload/jetson/'+p.name]=p
    for name in ('food_roi.example.json','food_roi.fixed_camera.candidate.json'):
        files['payload/config/'+name]=PAYLOAD/'config'/name
    for name in ('release_bundle.py','jetson_preflight.py','jetson_build.py','stage_release.py','camera_preflight.py'):
        p=HERE/name
        if p.exists():files['tools/'+name]=p
    for name in ('run_cpp_preview.py','run_secure_api.py','prepare_remote_config.py','serve_private.sh'):
        files['tools/'+name]=ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028'/name
    if (HERE/'camera_preflight.py').exists():
        for p in sorted((ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028/web_real').rglob('*')):
            if p.is_symlink():raise ValueError('web symlink forbidden')
            if p.is_file():files['web_real/'+p.relative_to(ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028/web_real').as_posix()]=p
        for name in ('DEPLOYMENT_RUNBOOK.md','CAMERA_DEPLOYMENT.md'):
            if (HERE/name).exists():files['docs/'+name]=HERE/name
    return files
def verify(folder):
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('bundle root symlink forbidden')
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('kind')!='FORCAT_OFFLINE_STAGING_V1':raise ValueError('manifest kind')
    entries=manifest['files']
    if not entries:raise ValueError('empty release')
    for name,metadata in entries.items():
        if not safe_name(name):raise ValueError('unsafe path')
        p=folder/name
        if any(x.is_symlink() for x in [p,*p.parents]) or not p.is_file():raise ValueError('missing file or symlink')
        if p.stat().st_size!=metadata['bytes'] or digest(p)!=metadata['sha256']:raise ValueError('integrity mismatch: '+name)
    paths=list(folder.rglob('*'))
    if any(p.is_symlink() for p in paths):raise ValueError('symlink in bundle')
    actual={p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    if actual!=set(entries)|{'manifest.json'}:raise ValueError('unexpected bundle files')
    return manifest
def create(destination):
    destination=Path(destination)
    files=collect()
    if destination.exists():raise ValueError('new directory required')
    destination.mkdir(parents=True,exist_ok=False)
    metadata={}
    for name,source in files.items():
        if not safe_name(name):raise ValueError('unsafe collected path')
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        metadata[name]={'bytes':target.stat().st_size,'sha256':digest(target)}
    manifest={'kind':'FORCAT_OFFLINE_STAGING_V1','production_changes':False,'physical_pass':False,
              'arm64_build':'NOT_VERIFIED','files':metadata}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    verify(destination)
    return manifest
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('create','verify'));p.add_argument('directory',type=Path);args=p.parse_args()
    result=create(args.directory) if args.command=='create' else verify(args.directory)
    print(json.dumps({'status':'PASS','files':len(result['files']),'physical_pass':False,'arm64_build':result['arm64_build']}))
if __name__=='__main__':main()
