"""Package this continuation only; no tests, devices, services or deployment."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
HERE=Path(__file__).resolve().parent;OVERNIGHT=HERE.parent;ROOT=OVERNIGHT.parent
KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029'
DOCS=('PROGRESS_REPORT.md','TEST_RESULTS.md','CHANGES_AND_PATCHES.md','BLOCKERS.md','NEXT_PHYSICAL_STEPS.md')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def count(name):
    text=(HERE/'evidence'/name).read_text(encoding='utf-8')
    return int(re.search(r'(\d+) passed',text).group(1))
def main():
    assert sha(KIT/'manifest.json')=='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
    assert sha(KIT/'web_hardware/gcc75_fix/transfer_manifest.json')=='de20b028df9a63f73a7b316d527ac980fc4d336120a40266c8935eccf8cf0322'
    baseline=read(HERE/'SOURCE_BASELINE.json');patch=[];changes=[]
    scratch=HERE/'evidence/patch_check';scratch.mkdir(exist_ok=True)
    for rel,meta in baseline.items():
        source=Path(meta['source']);target=HERE/'candidate'/rel
        assert sha(source)==meta['sha256'],'qualified source changed: '+str(source)
        original=scratch/'candidate'/rel;original.parent.mkdir(parents=True,exist_ok=True)
        if not original.exists():original.write_bytes(source.read_bytes())
        assert sha(original)==meta['sha256']
        if sha(target)!=meta['sha256']:
            patch.extend(difflib.unified_diff(source.read_text(encoding='utf-8').splitlines(True),target.read_text(encoding='utf-8').splitlines(True),
                fromfile='a/candidate/'+rel,tofile='b/candidate/'+rel))
            changes.append({'path':'candidate/'+rel,'before':meta['sha256'],'after':sha(target)})
    for rel in ('bridge/owner_behavior.h','flutter/offline_history_panel.dart'):
        target=HERE/'candidate'/rel
        patch.extend(difflib.unified_diff([],target.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/candidate/'+rel))
        changes.append({'path':'candidate/'+rel,'before':None,'after':sha(target)})
    (HERE/'candidate_changes.patch').write_bytes(''.join(patch).encode('utf-8'))
    checked=subprocess.run(['git','apply','--check',str(HERE/'candidate_changes.patch')],cwd=scratch,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (HERE/'evidence/patch_check.log').write_bytes(checked.stdout)
    assert checked.returncode==0,'patch dry-run failed'
    # Keep initial failures; count only unique successful cases, not repetitions.
    initial=count('backend_tests.log');assert initial==17
    latest={name:count('backend_'+name+'.log') for name in (
        'test_cpp_to_sqlite_api_exports_actual_contract_cases',
        'test_mock_manual_feed_ack_final_duplicate_disconnect_and_histories',
        'test_actual_cpp_session_timeline_through_cached_api',
        'test_cpp_closed_loop_failure_never_becomes_api_success',
        'test_exported_contract_time_domains_and_error_reasons')}
    assert sum(latest.values())==10
    current=read(HERE/'result.json')
    assert current['flutter_selected']==9 and current['flutter_analyze']=='PASS_NO_ISSUES'
    assert current['native_groups']==11 and current['native_checks']==158 and current['new_timeline_cases']==6
    maintain=read(KIT/'maintenance_readiness/validation/result.json')
    assert maintain['new_fake_service_tests_passed']==21
    summary={'VERIFIED_PASS':{'Windows_CPP14_builds':True,'Flutter_analyze':'NO_ISSUES',
            'source_patch_dry_run':True,'qualified_inputs_unchanged':True},
        'SIMULATION_PASS':{'maintenance_fake_service_tests':21,'native_logic_groups':11,'native_logic_checks':158,
            'session_timeline_cases':6,'backend_unique_cases':initial-1+sum(latest.values()),
            'Flutter_unique_cases':12},
        'count_method':{'backend_unchanged_wire_cases':16,'backend_latest_targeted':latest,
            'Flutter_latest_ASGI_widgets':8,'Flutter_latest_timestamp_case':1,
            'Flutter_retained_unaffected_export_history_ACK_cases':3,
            'initial_harness_failures_preserved':True,'not_a_claim_of_final_full_suite_rerun':True},
        'NOT_RUN':['new candidate ARM64/GCC7.5','OpenCV/TensorRT/camera target runtime','maintenance real services/Serial','deployment'],
        'BLOCKED':['owner-cat dataset/enrolled identity model','current running-bank/security/electrical flash gates'],
        'NEEDS_PHYSICAL_VALIDATION':['35g closed-loop mechanics/calibration/overshoot','ROM recovery and physical rollback'],
        'APP_FLASH':'NO_GO','physical_pass':False,'serial_opened':False,'camera_opened':False,
        'services_changed':False,'production_changed':False,'old_qualified_tests_rerun':False,
        'candidate_changes':changes}
    write(HERE/'verification_summary.json',summary)
    skipped={'.dart_tool','build','__pycache__','native','patch_check'}
    paths=[p for p in HERE.rglob('*') if p.is_file() and not any(x in skipped for x in p.relative_to(HERE).parts)
           and p.name not in ('ARTIFACT_MANIFEST.json','NEW_ARTIFACTS_SHA256SUMS')]
    paths+=[OVERNIGHT/name for name in DOCS]
    assert all(p.is_file() for p in paths)
    files={p.relative_to(OVERNIGHT).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(paths)}
    write(HERE/'ARTIFACT_MANIFEST.json',{'kind':'OVERNIGHT_CONTINUATION_ONLY',
        'qualified_590_manifest_unchanged':sha(KIT/'manifest.json'),
        'maintenance_package_integrity_sha256':sha(KIT/'maintenance_readiness/INTEGRITY.json'),
        'scope':'NEW_SOURCE_FIXTURES_LOGS_DOCS_NOT_PRODUCTION_OR_HARDWARE_ACCEPTANCE','files':files})
    (HERE/'NEW_ARTIFACTS_SHA256SUMS').write_bytes(''.join(v['sha256']+'  '+k+'\n' for k,v in sorted(files.items())).encode())
    # Verify the new package, not the old qualified test suites.
    for name,meta in files.items():assert sha(OVERNIGHT/name)==meta['sha256']
    print(json.dumps({'new_package_files_checked':len(files),'package_manifest_sha256':sha(HERE/'ARTIFACT_MANIFEST.json'),
        'SIMULATION_PASS':summary['SIMULATION_PASS'],'qualified_manifest_unchanged':True,'APP_FLASH':'NO_GO'},indent=2))
if __name__=='__main__':main()
