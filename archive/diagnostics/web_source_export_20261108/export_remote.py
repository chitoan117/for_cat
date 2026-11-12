from pathlib import Path
import hashlib,json,tarfile,urllib.request,sys

project=Path('/home/toan/for_cat')
r=project/'evidence/web_source_export_20261108';r.mkdir(exist_ok=True)
archive=r/'backend_release.tar.gz'
exclude={'__pycache__','.pytest_cache','.git','node_modules','data','models','.venv','snapshots'}
files=[]
def add_tree(tar,source,dest,extensions=None):
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if not p.is_file() or p.is_symlink() or any(x in exclude for x in rel.parts):continue
        if p.name.startswith('.env') or p.suffix in ('.pyc','.db','.sqlite','.pem','.key','.engine','.onnx'):continue
        if extensions is not None and p.suffix.lower() not in extensions:continue
        name=str(Path(dest)/rel)
        tar.add(p,arcname=name,recursive=False)
        files.append({'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':str(p)})
with tarfile.open(archive,'w:gz') as tar:
    for folder in ('app','tools','tests','device','bringup'):
        add_tree(tar,project/'jetson'/folder,'backend/jetson/'+folder)
    for p in sorted((project/'jetson').glob('requirements*.txt')):
        tar.add(p,arcname='backend/jetson/'+p.name,recursive=False)
    add_tree(tar,project/'jetson/ai','backend/jetson/ai',{'.py','.cpp','.h','.md','.json'})
    add_tree(tar,project/'ai','backend/ai',{'.py','.cpp','.h','.md','.json','.yaml','.yml','.txt'})
    for name in ('pytest.ini','ruff.toml','requirements-dev.txt','requirements-quality.txt'):
        p=project/name
        if p.is_file():tar.add(p,arcname='backend/'+name,recursive=False)
    for name in ('run_existing_ai.sh',):
        p=project/'scripts'/name
        if p.is_file():tar.add(p,arcname='backend/scripts/'+name,recursive=False)
    add_tree(tar,project/'.native-build/flutter/four_ultrasonic_20261027_r2','web_release')
with urllib.request.urlopen('http://127.0.0.1:8000/openapi.json',timeout=10) as response:
    (r/'openapi.json').write_bytes(response.read())
(r/'remote_manifest.json').write_text(json.dumps({'python':sys.version,'files':files},indent=2))
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
