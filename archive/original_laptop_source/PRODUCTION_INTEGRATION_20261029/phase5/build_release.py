"""Windows-only packaging of the exact post-Phase4 sources. No target operations."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid
HERE=Path(__file__).resolve().parent;SESSION=HERE.parent;ROOT=SESSION.parent
PAYLOAD=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'
sys.path.insert(0,str(HERE/'tools'))
from integrity import sha,verify,write_new,KIND

EXCLUDE={'__pycache__','.git','.pio','.venv','node_modules','data','models','build'}
SOURCE_SUFFIX={'.py','.h','.hpp','.cpp','.sh','.txt','.json','.html','.js','.css','.svg','.yaml','.in','.md'}
def tree(source,prefix):
    files={}
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if any(x.startswith('.') or x in EXCLUDE for x in rel.parts):continue
        if p.is_symlink():raise ValueError('source symlink: '+str(p))
        if p.is_file() and p.suffix in SOURCE_SUFFIX:
            if p.name in ('.env','access.json','server-env.json','runtime.json') or p.suffix in ('.token','.engine','.db'):raise ValueError('private/runtime file in source selection')
            files[prefix+'/'+rel.as_posix()]=p
    return files
def collect():
    phase4=json.loads((SESSION/'phase4/result.json').read_text())
    # Preserve the qualification scope; do not bless an edited source under old PASS.
    for name,digest in phase4['source_sha256'].items():
        if sha(name)!=digest:raise ValueError('Phase4 evidence stale for '+name)
    files=tree(PAYLOAD/'jetson/app','payload/jetson/app')
    files.update(tree(PAYLOAD/'jetson/device','payload/jetson/device'))
    files.update(tree(PAYLOAD/'jetson/tools','payload/jetson/tools'))
    files.update(tree(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/include','firmware_include'))
    files.update(tree(ROOT/'OFFLINE_REVIEW_20261024/project/jetson/ai','ai_reference'))
    for name in ('food_roi.example.json','food_roi.fixed_camera.candidate.json'):
        files['payload/config/'+name]=PAYLOAD/'config'/name
    # Current Flutter source for traceability + already qualified REAL/MOCK assets.
    frontend=Path(r'D:\DA_KT_NC\feeder_demo')
    files.update(tree(frontend/'lib','frontend_source/lib'))
    files['frontend_source/pubspec.yaml']=frontend/'pubspec.yaml'
    files['frontend_source/pubspec.lock']=frontend/'pubspec.lock'
    for mode in ('real','mock'):
        root=SESSION/'phase4'/('web_'+mode)
        if sha(root/'main.dart.js')!=phase4['web_builds'][mode]['main_dart_js_sha256']:raise ValueError('wrong Flutter artifact')
        for p in sorted(root.rglob('*')):
            if p.is_symlink():raise ValueError('web symlink')
            if p.is_file():files['web/'+mode+'/'+p.relative_to(root).as_posix()]=p
    files.update(tree(HERE/'tools','tools'));files.update(tree(HERE/'systemd','systemd'));files.update(tree(HERE/'docs','docs'))
    for name in ('test_ai_contract.py','test_state_wire.cpp','test_fusion_compat.cpp','test_fault_recovery.py','test_resources.cpp','test_stream_resources.py','test_phase4_api.py'):
        files['qualification/'+name]=SESSION/name
    files['qualification/phase4_result.json']=SESSION/'phase4/result.json'
    files['qualification/phase4_api_fixture.json']=SESSION/'phase4/api_contract_fixture.json'
    return files
def category(name):
    if name.startswith('ai_reference/shadow/'):return 'D','ROI/geometry, original-coordinate decoding',['C++14','TensorRT','OpenCV4']
    if name.startswith('ai_reference/'):return 'A','Preserved original detector and latency dependencies',['C++14','TensorRT','CUDA','OpenCV4']
    if name.startswith('payload/jetson/device/'):
        if any(x in name for x in ('preview_','roi_ai_source','state_wire')):return 'B','Single capture, framed producer, bounded preview',['C++14','A','D','json-c']
        return 'A','Native bridge/tap and policy dependencies',['C++14','json-c','sqlite3','firmware_include']
    if 'ai_frame' in name:return 'C','Compatible framed stdout canonical state adapter',['Python3.11','sqlite3','OS flock']
    if name.startswith('schema/') or '/storage/' in name:return 'F','SQLite additive schema/cache compatibility',['sqlite3>=3.24','Python3.11']
    if '/camera/' in name or 'runtime_config' in name:return 'I','Private same-origin video authorization',['FastAPI','Starlette','VIEW_CAMERA']
    if name.startswith('payload/jetson/app/'):return 'E','Authoritative FastAPI routes/services/models',['Python3.11','fastapi','pydantic2','starlette']
    if name.startswith(('web/','frontend_source/')):return 'G','Post-Phase4 Flutter artifacts/source; serve web/real only',['same-origin HTTPS','FastAPI static /flutter/']
    if name.startswith('systemd/'):return 'H','User service override template; explicit activation only',['systemctl --user','managed_runtime.py']
    return 'J','Deployment, qualification or source dependency',['manifest integrity','operator confirmation']
def schema(output):
    sys.path.insert(0,str(PAYLOAD/'jetson'))
    from app.main import create_app
    from app.config import HardwareConfig
    from app.camera.live_stream import FrameHub,VideoSettings
    from app.camera.remote_access import RemotePolicy
    from app.ai_frame_contract import StateTap
    from app.dry_run_requests import DryRunRequests
    work=HERE/'work';work.mkdir(exist_ok=True)
    # Retain this generated LOCAL sandbox DB as packaging evidence.
    p=work/('schema_'+uuid.uuid4().hex+'.sqlite3')
    app=create_app(db_path=p,hardware=HardwareConfig(),live_camera=FrameHub(VideoSettings()),remote_policy=RemotePolicy(),scheduled_worker_enabled=False)
    StateTap(p,'SCHEMA_TEST',lambda:1).disconnected()
    with sqlite3.connect(p) as db:
        DryRunRequests.ensure_schema(db)
        rows=db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        tables={name:{'ddl':sql,'columns':[{'name':r[1],'type':r[2].upper(),'pk':r[5]} for r in db.execute('PRAGMA table_info("'+name+'")')]} for name,sql in rows}
    db.close()
    app.state.records.close();app.state.store.close()
    folder=output/'schema';folder.mkdir()
    write_new(folder/'contract.json',{'schema_strategy':'EXISTING_TABLES_COMPATIBLE_ADDITIVE_ONLY','destructive_migration':False,'tables':tables})
    (folder/'additive_reference.sql').write_text('-- Reference only: application initialization owns CREATE IF NOT EXISTS. No DROP/ALTER/DELETE.\n'+
        '\n'.join(t['ddl'].replace('CREATE TABLE ','CREATE TABLE IF NOT EXISTS ',1)+';' for t in tables.values())+'\n',encoding='utf-8')
def create(output,resume=False):
    output=Path(output)
    selected=collect()
    if output.exists():
        if not resume or (output/'manifest.json').exists():raise ValueError('new release directory required; preserve existing user work')
        # Only resume our interrupted, exact source copy; do not overwrite any
        # modified/unfamiliar file or a finalized release.
        for p in output.rglob('*'):
            if p.is_symlink():raise ValueError('cannot resume symlink')
            if p.is_file():
                name=p.relative_to(output).as_posix()
                if name not in selected or sha(p)!=sha(selected[name]):raise ValueError('unfamiliar/modified incomplete file '+name)
    else:output.mkdir(parents=True,exist_ok=False)
    origins={}
    for name,p in selected.items():
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(p,target)
        origins[name]=str(p)
    schema(output)
    write_new(output/'dependencies.json',{'python_minimum':'3.11','python_packages':['fastapi','starlette','pydantic>=2','uvicorn'],
        'native':['g++ C++14','pkg-config opencv4 json-c sqlite3','CUDA10.2 runtime/headers','TensorRT runtime/headers'],
        'system':['systemctl --user','systemd-analyze','fuser','v4l2-ctl','ldconfig'],'automatic_install':False})
    entries={}
    for p in sorted(output.rglob('*')):
        if not p.is_file():continue
        name=p.relative_to(output).as_posix();group,role,deps=category(name)
        entries[name]={'source_path':origins.get(name,'GENERATED_FROM_CURRENT_AUTHORITATIVE_SOURCE'),
            'destination':'${RELEASE_DIR}/'+name,'sha256':sha(p),'bytes':p.stat().st_size,'group':group,
            'role':role,'dependencies':deps,'overwrites_production':False,'requires_arm64_build':p.suffix in ('.cpp','.h','.hpp')}
        if name.startswith('systemd/'):
            entries[name]['activation_destination']='${HOME}/.config/systemd/user/{for-cat-ai,for-cat-api}.service.d/90-forcat-rc-v2.conf'
            entries[name]['activation_overwrites_existing']='EXPLICIT_CUTOVER_ONLY_AFTER_VERIFIED_BACKUP'
    manifest={'kind':KIND,'release':'release_candidate_v2','qualification':'POST_PHASE4_36_BACKEND_33_FLUTTER',
        'arm64_build':'NOT_VERIFIED','physical_pass':False,'telemetry_blocker':'HX711_REFERENCE is not diag_current_hardware; never bypass parser',
        'files':entries}
    write_new(output/'manifest.json',manifest)
    (output/'manifest.sha256').write_text(sha(output/'manifest.json')+'\n')
    (output/'SHA256SUMS').write_text(''.join(m['sha256']+'  '+n+'\n' for n,m in sorted(entries.items())))
    verify(output);return manifest
def refresh_draft(output):
    # Qualification may fix deployment-tool defects. Refresh only this verified
    # draft from its explicit source map; never overwrite an edited release.
    output=Path(output);manifest=verify(output);selected=collect()
    generated={'schema/contract.json','schema/additive_reference.sql','dependencies.json'}
    if set(manifest['files'])!=set(selected)|generated:raise ValueError('draft file set changed; owner review required')
    for name,source in selected.items():
        if manifest['files'][name]['source_path']!=str(source):raise ValueError('draft source mapping changed')
        if sha(output/name)!=sha(source):shutil.copyfile(source,output/name)
        manifest['files'][name]['sha256']=sha(output/name)
        manifest['files'][name]['bytes']=(output/name).stat().st_size
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'manifest.sha256').write_text(sha(output/'manifest.json')+'\n')
    (output/'SHA256SUMS').write_text(''.join(m['sha256']+'  '+n+'\n' for n,m in sorted(manifest['files'].items())))
    verify(output);return manifest
if __name__=='__main__':
    out=SESSION/'release_candidate_v2'
    result=refresh_draft(out) if '--refresh-draft' in sys.argv else create(out,'--resume-incomplete' in sys.argv)
    print(json.dumps({'release':str(out),'files':len(result['files']),'manifest_sha256':sha(out/'manifest.json'),'physical_pass':False}))
