"""Final source/artifact/log integrity receipt only; no rebuild/retest/live IO."""
from datetime import datetime,timezone
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent;WS=ROOT.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');args=parser.parse_args()
result_name='FINAL_RESULT.json' if args.final else 'RESULT.json'
patch_name='SOURCE_CHANGES_FINAL.patch' if args.final else 'SOURCE_CHANGES.patch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((ROOT/'BASELINE.json').read_text())
for name,digest in base['inputs'].items():assert sha(Path(name))==digest,name
manual=Path(base['manual_image']);assert sha(manual)==base['manual_sha256']
native=json.loads((ROOT/'tests_command_progress/result.json').read_text())
flutter=json.loads((ROOT/'flutter_command_progress/result.json').read_text())
build=json.loads((ROOT/'firmware_build_inert_macro_fixed/result.json').read_text())
bridge=json.loads((ROOT/'bridge_link_tests/result.json').read_text())
for value in (native,flutter,build,bridge):assert value.get('status',value.get('build'))=='PASS_OFFLINE'
image=Path(build['image']);assert sha(image)==build['image_sha256'] and image.stat().st_size==377840
for rel,digest in build['source_sha256'].items():assert sha(ROOT/'firmware'/rel)==digest,rel
assert sha(ROOT/'backend/ai_contract.py')==json.loads((ROOT/'AI_SOURCE.json').read_text())['sha256']
assert sha(ROOT/'firmware/include/m4/dispense_bench.h')==sha(WS/'CANDIDATE_R2_OFFLINE_HARDENING_20261030/candidate/firmware/include/m4/dispense_bench.h')
original=ROOT.parent/'INTEGRATED_MANUAL_CANDIDATE/firmware'
patch=[];changes=[]
selected=[p for d in ('backend','bridge','tests','flutter/lib','flutter/test','firmware/include','firmware/src')
          for p in (ROOT/d).rglob('*') if p.is_file() and p.suffix in ('.py','.h','.cpp','.dart')]
for p in sorted(selected):
    rel=p.relative_to(ROOT).as_posix();before='';source=None
    if rel.startswith('firmware/'):
        source=original/rel[len('firmware/'):]
        if source.is_file():before=source.read_text(encoding='utf-8')
    elif rel=='backend/wire.py':
        source=WS/'CANDIDATE_R2_OFFLINE_HARDENING_20261030/candidate/backend/app/serial_link/protocol.py';before=source.read_text()
    elif rel=='backend/ai_contract.py':
        source=WS/'CANDIDATE_R2_OFFLINE_HARDENING_20261030/candidate/backend/app/ai_frame_contract.py';before=source.read_text()
    after=p.read_text(encoding='utf-8')
    if before!=after:
        patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
        changes.append(dict(path=rel,sha256=sha(p),baseline=str(source) if before else None))
with (ROOT/patch_name).open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(patch))
files={}
for p in ROOT.rglob('*'):
    if not p.is_file() or p.name==result_name:continue
    rel=p.relative_to(ROOT)
    if any(x in ('.pio','.dart_tool','build','__pycache__') for x in rel.parts) or p.suffix in ('.exe','.pdb','.pyc','.db','.db-wal','.db-shm','.elf'):continue
    files[rel.as_posix()]={'bytes':p.stat().st_size,'sha256':sha(p)}
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='PASS_OFFLINE',
    native_integration_cases=native['new_pytest_cases'],flutter_tests=flutter['new_flutter_tests'],
    flutter_analyze=flutter['analyze'],flutter_web_build=flutter['build_web'],bridge_callback_assertions=bridge['new_callback_assertions'],
    old_suites_rerun=False,old_manual_image_unchanged=True,manual_image_sha256=sha(manual),
    new_inert_image=build['image'],new_inert_image_sha256=sha(image),new_inert_image_bytes=image.stat().st_size,
    new_image_physical_enable=False,locked_source_inputs_verified=len(base['inputs']),
    physical_pass=False,production_accessed=False,services_changed=False,serial_opened=False,camera_opened=False,
    APP_FLASH='NO_GO',changes=changes,files=dict(sorted(files.items())),
    evidence=dict(protocol='tests_command_progress/result.json',flutter='flutter_command_progress/result.json',
                  firmware='firmware_build_inert_macro_fixed/result.json',bridge='bridge_link_tests/result.json'))
with (ROOT/result_name).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ('status','native_integration_cases','flutter_tests','flutter_web_build',
    'bridge_callback_assertions','old_manual_image_unchanged','new_inert_image_sha256','locked_source_inputs_verified','APP_FLASH')},indent=2))
