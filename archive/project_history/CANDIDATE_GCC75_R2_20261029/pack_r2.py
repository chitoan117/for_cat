"""One-shot source delta packaging. No rebuild, baseline updates or deployment."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent;WORKSPACE=ROOT.parent
OLD=WORKSPACE/'OVERNIGHT_ENGINEERING_20261029/offline_continuation'
KIT=WORKSPACE/'HARDWARE_PHYSICAL_BRINGUP_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def main():
    if (ROOT/'TRANSFER_MANIFEST.json').exists() or (ROOT/'R2_SOURCE_DELTA.zip').exists():raise ValueError('R2 package already sealed; create a new revision, no overwrite')
    assert sha(KIT/'manifest.json')=='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
    assert sha(KIT/'web_hardware/gcc75_fix/transfer_manifest.json')=='de20b028df9a63f73a7b316d527ac980fc4d336120a40266c8935eccf8cf0322'
    assert sha(OLD/'ARTIFACT_MANIFEST.json')=='c12fc0b7b748686b97eac013e2e60351eb22c254c767eaff121d013525628a54'
    for name,meta in read(OLD/'ARTIFACT_MANIFEST.json')['files'].items():assert sha(OLD.parent/name)==meta['sha256'],'locked overnight input changed: '+name
    provenance=read(ROOT/'SOURCE_PROVENANCE.json')['inputs']
    changes=[];patch=[]
    for rel,meta in provenance.items():
        original=Path(meta['source']);assert sha(original)==meta['sha256'],'source changed '+str(original)
        target=ROOT/rel
        if sha(target)!=meta['sha256']:
            changes.append({'path':rel,'before':meta['sha256'],'after':sha(target)})
            patch.extend(difflib.unified_diff(original.read_text(encoding='utf-8').splitlines(True),target.read_text(encoding='utf-8').splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
    (ROOT/'R2_VS_OVERNIGHT.patch').write_bytes(''.join(patch).encode('utf-8'))
    core=('telemetry.h','ultrasonic_telemetry.h','diagnostic_session.h','food_roi.h','feed_policy.h','decision_logic.h','approach_fusion.h','roi_species.h','esp32_bridge.cpp','parser_replay.cpp','test_session.cpp','test_food_roi.cpp')
    for name in core:assert sha(ROOT/'candidate/bridge'/name)==sha(KIT/'web_hardware/bridge_candidate'/name),'unexpected R1 core change '+name
    write(ROOT/'CHANGESET.json',{'revision':'GCC75_R2','changes_vs_overnight':changes,
        'unchanged_R1_core':{n:sha(ROOT/'candidate/bridge'/n) for n in core},
        'reason_ordinal_policy':'PERSISTENCE_FAULT19 unchanged, TARGET_OVERSHOOT20 appended, never a FEED_STATUS wirecode',
        'APP_FLASH':'NO_GO','ARM64_NATIVE_TEST_PASS':'NOT_RUN'})
    win=ROOT/'validation_windows_20261030_005707'
    result=read(win/'result.json')
    assert result['WINDOWS_OFFLINE_TEST_PASS'] is True and result['backend_tests']==47 and result['flutter_tests']==28
    assert result['native']['r2_dispense']=={'cases':16,'checks':126} and result['flutter_analyze']=='PASS_NO_ISSUES'
    tooling=read(ROOT/'WINDOWS_TOOLING_RESULT.json');assert tooling['tests_passed']==11
    write(ROOT/'WINDOWS_QUALIFICATION.json',{'revision':'GCC75_R2','executed_result':result,
        'whole_posix_bridge_on_Windows':'NOT_RUN','tooling':tooling,
        'raw_evidence_directory':str(win),'raw_log_sha256':{p.name:sha(p) for p in sorted(win.glob('*.log'))},
        'ARM64_NATIVE_TEST_PASS':'NOT_RUN','APP_FLASH':'NO_GO'})
    for name in ('native_arm64_r2.py','native_checks.py','verify_transfer.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'),feature_version=(3,6))
    write(ROOT/'FIXTURE_PROVENANCE.json',{'revision':'GCC75_R2','source':'SIMULATED','execution_context':'OFFLINE_TEST_ONLY',
        'physical_pass':False,'wire_mode':'diag_current_hardware','kit_profile':'diag_four_ultrasonic',
        'wire_not_rewritten_to_add_simulation_protocol_fields':True,
        'fixtures':{p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size,'origin':'SYNTHETIC_FIRMWARE_LOOP_OR_EXPLICIT_SYNTHETIC_MUTATION'} for p in sorted((ROOT/'fixtures').iterdir()) if p.is_file()},
        'API_UI_generated_fixture_location':'NEW validation_windows_*/fixtures, output not source input'})
    excluded={'TRANSFER_MANIFEST.json','TRANSFER_MANIFEST.sha256','R2_SOURCE_DELTA.zip','R2_SOURCE_DELTA.zip.sha256','R2_PACKAGE_RESULT.json','DELTA_FILES.txt'}
    payload=[]
    for p in sorted(ROOT.rglob('*')):
        parts=p.relative_to(ROOT).parts
        if any(x in ('.dart_tool','build','__pycache__','.pytest_cache') or x.startswith('validation_') for x in parts):continue
        if p.is_file() and p.name not in excluded and p.name not in ('pubspec.lock','.flutter-plugins-dependencies') and p.suffix not in ('.exe','.pyc'):
            payload.append(p.relative_to(ROOT).as_posix())
    all_members=sorted(payload+['DELTA_FILES.txt','TRANSFER_MANIFEST.json','TRANSFER_MANIFEST.sha256'])
    (ROOT/'DELTA_FILES.txt').write_bytes(('\n'.join(all_members)+'\n').encode('utf-8'))
    payload.append('DELTA_FILES.txt')
    write(ROOT/'TRANSFER_MANIFEST.json',{'kind':'FORCAT_R2_SOURCE_DELTA','revision':'GCC75_R2',
        'scope':'NEW_ROOT_SELF_CONTAINED_NATIVE_SOURCE_AND_OFFLINE_API_UI_REVIEW_ONLY',
        'ARM64_NATIVE_TEST_PASS':'NOT_RUN','APP_FLASH':'NO_GO','physical_pass':False,
        'files':{name:{'bytes':(ROOT/name).stat().st_size,'sha256':sha(ROOT/name)} for name in sorted(payload)}})
    digest=sha(ROOT/'TRANSFER_MANIFEST.json')
    (ROOT/'TRANSFER_MANIFEST.sha256').write_bytes((digest+'\n').encode('ascii'))
    from verify_transfer import verify
    transfer=verify(expected=digest)
    archive=ROOT/'R2_SOURCE_DELTA.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in all_members:z.write(ROOT/name,name)
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist())==all_members
        assert z.testzip() is None
        for name in all_members:assert hashlib.sha256(z.read(name)).hexdigest()==sha(ROOT/name)
    (ROOT/'R2_SOURCE_DELTA.zip.sha256').write_bytes((sha(archive)+'  R2_SOURCE_DELTA.zip\n').encode('ascii'))
    summary={'revision':'GCC75_R2','transfer':transfer,'zip_members':len(all_members),
        'zip_bytes':archive.stat().st_size,'zip_sha256':sha(archive),
        'Windows':{'backend_tests':47,'Flutter_tests':28,'R2_dispense_cases':16,'R2_dispense_checks':126,'tooling_tests':11},
        'source_inputs_preserved':True,'R2_ARM64_NATIVE_TEST_PASS':'NOT_RUN','APP_FLASH':'NO_GO'}
    write(ROOT/'R2_PACKAGE_RESULT.json',summary)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
