"""Seal new source/evidence only. No tests, devices, baseline modification or deployment."""
import ast,difflib,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;WS=ROOT.parent
sys.path.insert(0,str(ROOT/'tools'))
import safe_release as release
REPORTS=('PROGRESS.md','SAFETY_AUDIT.md','E2E_INTEGRATION_RESULTS.md','FLUTTER_RESULTS.md',
    'AI_BEHAVIOR_RESULTS.md','BUGS_FIXED.md','RELEASE_READINESS.md','NEXT_OWNER_ACTIONS.md')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def main():
    if (ROOT/'release_source').exists() or (ROOT/'R2_HARDENING_SOURCE.zip').exists():raise ValueError('release already sealed; use a new revision')
    base=read(ROOT/'BASELINE_INPUTS.json');changes=[];patch=[]
    for rel,meta in base['inputs'].items():
        original=Path(meta['source']);assert sha(original)==meta['sha256'],'locked input changed: '+str(original)
        current=ROOT/rel
        if sha(current)!=meta['sha256']:
            changes.append({'path':rel,'before':meta['sha256'],'after':sha(current)})
            if current.suffix in ('.h','.cpp','.py','.dart','.yaml'):
                patch+=difflib.unified_diff(original.read_text(encoding='utf-8').splitlines(True),current.read_text(encoding='utf-8').splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)
    for name,meta in read(ROOT/'SHARED_UI_BASELINE.json').items():assert sha(Path(meta['source']))==meta['sha256'] and sha(ROOT/'candidate/flutter_shared/lib'/name)==meta['sha256']
    additions=[]
    for folder in ('candidate','tests','tools'):
        for path in sorted((ROOT/folder).rglob('*')):
            rel=path.relative_to(ROOT)
            if not path.is_file() or path.suffix not in ('.py','.h','.cpp','.dart','.yaml'):continue
            if any(x in ('.dart_tool','build','__pycache__') for x in rel.parts) or rel.as_posix() in base['inputs']:continue
            additions.append({'path':rel.as_posix(),'before':None,'after':sha(path)})
            patch+=difflib.unified_diff([],path.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+rel.as_posix())
    r2=WS/'CANDIDATE_GCC75_R2_20261029'
    assert sha(r2/'TRANSFER_MANIFEST.json')==base['R2_manifest_sha256'] and sha(r2/'R2_SOURCE_DELTA.zip')==base['R2_zip_sha256']
    assert sha(WS/'HARDWARE_PHYSICAL_BRINGUP_20261029/manifest.json')=='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
    safety=read(ROOT/'evidence/fixed_safety_pm5/result.json');core=read(ROOT/'evidence/native_core/result.json')
    backend=read(ROOT/'evidence/backend_20261030_112615/result.json');extras=read(ROOT/'evidence/python_extras/result.json')
    flutter=read(ROOT/'evidence/flutter_20261030_114952/result.json');probe=read(ROOT/'evidence/flutter_20261030_121738/result.json')
    behavior=read(ROOT/'evidence/behavior/result.json')
    assert (safety['cases'],safety['checks'],core['mass_cases'],core['mass_checks'])==(12,101,11,58)
    assert core['session_checks']==9 and core['stream_records']==24 and backend['cases']==22 and extras['new_cases']==17
    assert flutter['tests']==21 and probe['tests']==1 and behavior['checks']==134
    assert read(ROOT/'evidence/release_tests/result.json')['cases']==35
    assert read(ROOT/'evidence/release_tests_native/result.json')['cases']==2
    assert read(ROOT/'evidence/release_tests_devices/result.json')['cases']==20
    (ROOT/'SOURCE_CHANGES.patch').write_bytes(''.join(patch).encode('utf-8'))
    write(ROOT/'CHANGESET.json',{'base':'GCC75_R2','revision':'R2_OFFLINE_HARDENING_PM5','changes':changes,'additions':additions,
        'mass_policy':read(ROOT/'fixtures/feeding_policy.json'),'wire_protocol_changed':False,
        'ABI':'private controller/session layout/semantics changed: rebuildall, no R1/R2 object mixing',
        'APP_FLASH':'NO_GO','ARM64_NATIVE_TEST_PASS':'NOT_RUN'})
    summary={'base':'GCC75_R2','revision':'R2_OFFLINE_HARDENING_PM5',
        'VERIFIED_PASS':['Windows C++14 strict compilation','Flutter analyze','new archive/source integrity'],
        'SIMULATION_PASS':{'controller_cases':12,'controller_checks':101,'mass_cases':11,'mass_checks':58,
            'session_checks':9,'connected_transport_snapshots':24,'behavior_checks':134,'backend_E2E_SQL_cases':22,
            'preference_and_extra_data_cases':17,'Flutter_unique_cases':22,'release_unique_cases':41},
        'count_notes':'component counts not added; Flutter21+newprobe1, release35+native2+newDOS4; targeted20 contains16repeatcases',
        'NOT_RUN':['hardening ARM64/GCC7.5','whole POSIX Bridge on Windows','target backend/runtime/GPU/camera','deployment'],
        'BLOCKED':['real owner enrollment/model','actual running bank/security/eFuse/ECHO/power/RAM maintenance gates'],
        'NEEDS_PHYSICAL_VALIDATION':['closed loop/mechanism/settling/inertial overshoot','NVS/power-loss/recovery'],
        'source_inputs_unchanged':True,'production_changed':False,'serial_opened':False,'camera_opened':False,
        'services_changed':False,'physical_pass':False,'APP_FLASH':'NO_GO'}
    write(ROOT/'VERIFICATION_SUMMARY.json',summary)
    for name in ('native_hardening.py','safe_release.py'):ast.parse((ROOT/'tools'/name).read_text(encoding='utf-8'),feature_version=(3,6))
    runtime_windows=[]
    import re
    for path in (ROOT/'candidate').rglob('*'):
        if path.is_file() and path.suffix in ('.py','.dart','.yaml') and not any(x in ('.dart_tool','build','__pycache__') for x in path.parts):
            if re.search(r'\b[A-Z]:[\\/](?:for_cat|DA_KT_NC|Users|dev)',path.read_text(encoding='utf-8')):runtime_windows.append(str(path))
    assert not runtime_windows,'absolute Windows runtime references'
    # Portable source package: no frozen forensic tools, Windows binaries/cache,
    # production DB or legacy qualified test entrypoints with old semantics.
    files=[]
    for path in (ROOT/'candidate').rglob('*'):
        rel=path.relative_to(ROOT)
        if not path.is_file() or any(x in ('.dart_tool','build','__pycache__') for x in rel.parts):continue
        if path.suffix in ('.py','.h','.cpp','.dart','.yaml','.json','.lock'):
            if str(rel.as_posix()).startswith('candidate/bridge/test_') or path.name=='parser_replay.cpp':continue
            if path.name.startswith('.flutter-plugins'):continue
            files.append(rel.as_posix())
    files += ['tools/safe_release.py','tools/native_hardening.py','BASELINE_INPUTS.json','SHARED_UI_BASELINE.json',
        'CHANGESET.json','SOURCE_CHANGES.patch','VERIFICATION_SUMMARY.json']+list(REPORTS)
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'fixtures').iterdir() if p.is_file()]
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').iterdir() if p.is_file() and p.suffix in ('.py','.cpp')]
    selected=('baseline_safety/result.json','fixed_safety_pm5/result.json','native_core/result.json',
        'baseline_sql_2/result.json','fixed_sql_2/result.json','baseline_preference.json','fixed_preference.json',
        'behavior/result.json','baseline_release.json','release_tests/result.json','release_tests_native/result.json',
        'release_tests_devices/result.json','backend_20261030_112615/result.json','python_extras/result.json',
        'flutter_20261030_114952/result.json','flutter_20261030_121738/result.json')
    files += ['evidence/'+name for name in selected]
    files=sorted(set(files));dest=ROOT/'release_source';dest.mkdir()
    for name in files:
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write((ROOT/name).read_bytes())
    entries={name:{'bytes':(dest/name).stat().st_size,'sha256':sha(dest/name)} for name in files}
    manifest={'kind':release.KIND,'base_revision':'GCC75_R2','revision':'R2_OFFLINE_HARDENING_PM5',
        'ARM64_NATIVE_TEST_PASS':'NOT_RUN','APP_FLASH':'NO_GO','files':entries}
    write(dest/release.MANIFEST,manifest);digest=sha(dest/release.MANIFEST)
    (dest/release.DIGEST).write_bytes((digest+'\n').encode('ascii'))
    release.directory(dest,digest)
    archive=ROOT/'R2_HARDENING_SOURCE.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files+[release.MANIFEST,release.DIGEST]):z.write(dest/name,name)
    archive_result=release.archive(archive,digest)
    # Actual safe roundtrip into a NEW owned directory, no tests rerun.
    extracted=ROOT/'release_roundtrip';release.extract(archive,extracted,digest)
    result={'revision':'R2_OFFLINE_HARDENING_PM5','archive':archive.name,'archive_bytes':archive.stat().st_size,
        'archive_sha256':sha(archive),'source_manifest_sha256':digest,'payload_files':len(files),
        'archive_roundtrip':'VERIFIED_PASS','archive_verification':archive_result,
        'R2_locked_unchanged':True,'ARM64_NATIVE_TEST_PASS':'NOT_RUN','APP_FLASH':'NO_GO'}
    write(ROOT/'PACKAGE_RESULT.json',result)
    (ROOT/'R2_HARDENING_SOURCE.zip.sha256').write_bytes((sha(archive)+'  '+archive.name+'\n').encode('ascii'))
    # Full local source/evidence inventory, including raw logs but excluding executables.
    local={}
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(x in ('release_source','release_roundtrip','.dart_tool','build','__pycache__') for x in rel.parts):continue
        if p.suffix in ('.exe','.o','.obj','.pyc') or p.name in ('LOCAL_INTEGRITY.json',):continue
        local[rel.as_posix()]={'bytes':p.stat().st_size,'sha256':sha(p)}
    write(ROOT/'LOCAL_INTEGRITY.json',{'kind':'NEW_WORKSPACE_ONLY','files':dict(sorted(local.items()))})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
