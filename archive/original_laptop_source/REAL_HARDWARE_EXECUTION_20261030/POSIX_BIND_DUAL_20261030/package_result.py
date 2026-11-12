"""New source/patch/evidence integrity only. No build, suite rerun or device IO."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent;P=ROOT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((ROOT/'BASELINE.json').read_text())
for p,digest in base['inputs'].items():assert sha(Path(p))==digest,p
for p,digest in base['locked_images'].items():assert sha(Path(p))==digest,p
bind=json.loads((ROOT/'bind_tests_safety_paths/result.json').read_text())
dual=json.loads((ROOT/'dual_tests_global_stop/result.json').read_text())
build=json.loads((ROOT/'dual_build_global_stop/result.json').read_text())
posix=json.loads((ROOT/'posix_syntax_object_only/result.json').read_text())
for item in (bind,dual,build,posix):assert item.get('status',item.get('build'))=='PASS_OFFLINE'
for rel,digest in build['source_sha256'].items():assert sha(ROOT/'firmware'/rel)==digest,rel
image=Path(build['image']);assert sha(image)==build['image_sha256'] and image.stat().st_size==423712
patch=[];changes=[]
candidates=[p for directory in ('bridge','backend','firmware/include','firmware/src','tests','compat') for p in (ROOT/directory).rglob('*')]
candidates += list(ROOT.glob('*.py'))+[ROOT/'manual_console_dual.py',ROOT/'firmware/platformio.ini']
for p in sorted(set(candidates)):
        if not p.is_file() or p.suffix not in ('.h','.cpp','.py','.def','.ini'):continue
        rel=p.relative_to(ROOT).as_posix();old=None
        if rel.startswith('bridge/'):
            old=P/'OFFLINE_BRIDGE_SERVO_PREP_20261030'/rel
            if p.name=='sole_owner_feed_link.h':old=P/'AUTONOMOUS_INTEGRATION_20261030'/rel
        elif rel.startswith('backend/'):old=P/'AUTONOMOUS_INTEGRATION_20261030'/rel
        elif rel.startswith('firmware/'):
            old=P/'INTEGRATED_MANUAL_CANDIDATE'/rel
            if p.name in ('dispense_bench.h','feed_link.h'):old=P/'AUTONOMOUS_INTEGRATION_20261030'/rel
        elif rel=='manual_console_dual.py':old=P/'INTEGRATED_MANUAL_CANDIDATE/manual_console.py'
        before=old.read_text(encoding='utf-8') if old and old.is_file() else ''
        after=p.read_text(encoding='utf-8')
        if before!=after:
            patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
            changes.append(dict(path=rel,baseline=str(old) if before else None,sha256=sha(p)))
with (ROOT/'SOURCE_CHANGES.patch').open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(patch))
files={}
for p in ROOT.rglob('*'):
    if not p.is_file() or p.name=='RESULT.json':continue
    rel=p.relative_to(ROOT)
    if any(x in ('.pio','__pycache__') for x in rel.parts) or p.suffix in ('.exe','.o','.pdb','.a','.elf','.pyc','.db','.db-wal','.db-shm'):continue
    files[rel.as_posix()]=dict(bytes=p.stat().st_size,sha256=sha(p))
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS_OFFLINE',
    actual_bridge_source_bound=True,full_bridge_new_integration_cases=bind['new_integration_cases'],new_dual_loop_cases=dual['new_dual_cases'],
    posix_branch_compile=posix['kind'],target_Linux_link='NOT_RUN',Jetson_ARM64_runtime='NOT_RUN',physical_pass=False,
    new_dual_image=str(image),new_dual_image_bytes=image.stat().st_size,new_dual_image_sha256=sha(image),
    feed_physical_enable=False,closure_provider_available=False,source_inputs_unchanged=len(base['inputs']),
    locked_images_match=base['locked_images'],old_suites_rerun=False,production_changed=False,serial_opened=False,
    services_changed=False,camera_opened=False,APP_FLASH='NO_GO',changes=changes,files=dict(sorted(files.items())))
with (ROOT/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ('status','actual_bridge_source_bound','full_bridge_new_integration_cases',
    'new_dual_loop_cases','new_dual_image_bytes','new_dual_image_sha256','source_inputs_unchanged','APP_FLASH')},indent=2))
