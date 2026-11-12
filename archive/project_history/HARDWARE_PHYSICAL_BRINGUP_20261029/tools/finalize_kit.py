"""Finalize artifact/source/evidence integrity only. No devices/flash/services.
Leaves production reports/readiness and the accepted RC completely untouched.
"""
import sys
sys.dont_write_bytecode=True
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from image_layout import sha,partitions,image_header,FLASH_SIZE
from build_windows import DEFAULT,PIO,ESPTOOL

KIT=Path(__file__).resolve().parents[1];ROOT=KIT.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    build=read(KIT/'build_result.json');source=read(KIT/'SOURCE_REFERENCE.json')
    native=read(KIT/'test_output/result_all.json')['native']
    tools=read(KIT/'test_output/result_tools.json') if (KIT/'test_output/result_tools.json').exists() else read(KIT/'test_output/result_all.json')
    assert not build['physical_pass'] and not build['flash_performed'] and build['pump_polarity_selected'] is None
    assert set(build['profiles'])==set(DEFAULT)
    for name,digest in build['firmware_source_sha256'].items():assert sha(KIT/'firmware'/name)==digest,'stale firmware '+name
    images={}
    for profile,layout in build['profiles'].items():
        folder=KIT/'artifacts'/profile
        for name,meta in layout['artifacts'].items():
            assert sha(folder/name)==meta['sha256'] and (folder/name).stat().st_size==meta['bytes']
        assert partitions((folder/'partitions.bin').read_bytes())==layout['partitions']
        assert image_header((folder/'firmware.bin').read_bytes())['flash_size_code']==4
        assert layout['application_partition']['offset']==layout['app_offset']
        assert layout['flash_size']==FLASH_SIZE and layout['factory_image_excluded']
        images[profile]=layout['artifacts']['firmware.bin']
    # Verify shared bootloader with the actual esptool decoder, without any port.
    p=subprocess.run([str(PIO),str(ESPTOOL),'--chip','esp32s3','image-info',str(KIT/'artifacts/diag_four_ultrasonic/bootloader.bin')],
        capture_output=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'},timeout=60)
    (KIT/'build_logs/bootloader_image_info.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'bootloader image inspection failed'
    # The snapshot authority and accepted release are read-only comparison roots.
    for name,meta in source['source_before_kit_changes'].items():assert sha(Path(meta['upstream']))==meta['sha256'],'upstream changed '+name
    rc=ROOT/'PRODUCTION_INTEGRATION_20261029/release_candidate_v2'
    assert sha(rc/'manifest.json')==source['accepted_rc_manifest_sha256']
    spec=importlib.util.spec_from_file_location('accepted_rc_integrity',rc/'tools/integrity.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.verify(rc)
    changes=[]
    for directory in ('src','include'):
        for path in (KIT/'firmware'/directory).rglob('*'):
            if path.is_file():
                rel=path.relative_to(KIT/'firmware').as_posix();old=source['source_before_kit_changes'].get(rel)
                if old is None or old['sha256']!=sha(path):changes.append(rel)
    changes+=['platformio.ini','kit_metadata.py']
    assert len(native['loop_cases'])==17 and len(native['rejected_unsafe_builds'])==6 and tools['python_tests']>=26
    for required in ('README.md','WINDOWS_BUILD.md','FLASH_AND_ROLLBACK.md','SENSOR_TESTS.md','ACTUATOR_PROCEDURES.md',
                     'HX711_EVIDENCE_NOTES.md','FINAL_HARDWARE_REPORT_TEMPLATE.md','OWNER_OBSERVATIONS_TEMPLATE.json'):
        assert (KIT/required).is_file()
    result={'milestone':'REAL_HARDWARE_PHYSICAL_VALIDATION_KIT','completed_at':datetime.now().astimezone().isoformat(),
        'HARDWARE_TEST_KIT_OFFLINE_READY':'YES','physical_pass':False,'flash_performed':False,'ssh_used':False,
        'serial_opened':False,'production_readiness_changed':False,'accepted_release_integrity':'PASS_UNCHANGED',
        'upstream_source_integrity':'PASS_UNCHANGED','kit_only_source_edits':changes,
        'windows_build':'PASS','profiles':images,'pump_image':'INERT_UNKNOWN_POLARITY_NO_GPIO7_TOUCH',
        'active_pump_artifacts_shipped':False,'native_fake_loop_cases_passed':17,'unsafe_build_guard_rejections':6,
        'python_tool_tests_passed':tools['python_tests'],'shell_syntax':'PASS_GIT_BASH_PARSE_ONLY',
        'bootloader_and_app_image_inspection':'PASS_OFFLINE_ESPTOOL','partition_validation':'PASS_MD5_BOUNDS_AND_SCONS_OFFSETS',
        'first_owner_command':'systemctl --user is-active for-cat-esp32-bridge.service',
        'hx711_owner_evidence':'OWNER_ACCEPTED_STATIC_PASS_35g_REFERENCE_34.981g; RAM_ONLY; no full weights retest; persistence and closed-loop35g NOT_VERIFIED',
        'remote_source_equality':'NOT_VERIFIED_NO_SSH','uart_transport_equality_to_ttyACM0':'NOT_VERIFIED_OWNER_USB_ID_REVIEW_REQUIRED',
        'hx711_current_ram_state':'UNKNOWN_AFTER_OWNER_REPORTED_ROM_RESETS_NOT_ASSUMED_PERSISTENT',
        'backup_recovery_handoff':'recovery/OPERATOR_HANDOFF.md',
        'full16MB_hardware_backup_status':'NOT_VERIFIED_OWNER_REPORTS_INCOMPLETE',
        'servo_production_lock':'LOCKED','pump_production_lock':'LOCKED',
        **{k:'NOT_VERIFIED' for k in ('FOUR_ULTRASONIC_PHYSICAL_PASS','PIR_PHYSICAL_PASS','BUZZER_PHYSICAL_PASS','SERVO_PHYSICAL_PASS','PUMP_PHYSICAL_PASS','ESP32_TELEMETRY_PASS')}}
    if (KIT/'HX711_ACCEPTANCE.json').exists():
        hx=read(KIT/'HX711_ACCEPTANCE.json')
        for key in ('HX711_PHYSICAL_STATIC_TEST','HX711_STATIC_MEASUREMENT_PHYSICAL_PASS','HX711_35G_REFERENCE_MEASUREMENT','HX711_MEASUREMENT_ACCURACY_ACCEPTED','HX711_RETEST_REQUIRED','HX711_CALIBRATION_PERSISTENCE','HX711_CLOSED_LOOP_DISPENSE_35G'):
            result[key]=hx[key]
        result['hx711_acceptance_record']='HX711_ACCEPTANCE.json'
        result['physical_pass_scope_note']='Kit preparation/backup is not physical acceptance; HX711 static measurement has separate OWNER-accepted PHYSICAL PASS.'
    if (KIT/'execution/OWNER_STATE.json').exists():
        result['first_owner_command']='WAIT_FOR_BACKUP_A_PROMPT_THEN_SAVE_EXISTING_EXIT_AND_COMPLETION_LOG_ONLY'
        result['current_execution_handoff']='PHYSICAL_EXECUTION_CHECKLIST.md'
        result['backup_A_latest_owner_report']='RUNNING_AT_LAST_REPORT_NOT_POLLED_NO_COMPLETION_RECEIVED'
    completed_pair=None
    if (KIT/'web_hardware/accepted_backup_pair.json').exists():
        from completed_backup_pair import validate_receipt as validate_completed_pair
        completed_pair=read(KIT/'web_hardware/accepted_backup_pair.json')
        validate_completed_pair(completed_pair['files'][0]['file'],completed_pair)
        result.update(full16MB_hardware_backup_status='PASS_OWNER_COMPLETED_AND_DIRECT_AB_FILE_HASH',
            backup_A_latest_owner_report='COMPLETED_NO_RUNNING_BACKUP_OWNER_CONFIRMED',
            first_owner_command='REVIEW_LOCAL_BACKUP_LAYOUT_AND_WEB_HANDOFF_NO_THIRD_READ_OR_OLD_EXITCODE',
            current_execution_handoff='web_hardware/BACKUP_AND_WEB_HANDOFF.md',
            backup_AB_sha256=completed_pair['sha256'],third_read_required=False,old_exitcode_requested=False)
    (KIT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if (KIT/'recovery/BASELINE_INTEGRITY.json').exists():
        recovery={'kind':'OPERATOR_HANDOFF_BACKUP_RECOVERY_OFFLINE_RESULT','completed_at':result['completed_at'],
            'original_kit_integrity':'PASS_196_FILES_BEFORE_RECOVERY_EDITS',
            'baseline_manifest_sha256':read(KIT/'recovery/BASELINE_INTEGRITY.json')['manifest_sha256'],
            'firmware_artifact_integrity':'PASS_UNCHANGED','new_sensor_app_sha256':images['diag_four_ultrasonic']['sha256'],
            'old_sensor_app_sha256_owner_reported':'73b4b65fb09c798b42345a1a3544f6d93ce0835f5d6651c3f53a01735527d621',
            'python_focused_tests_passed':tools['python_tests'],'native_and_firmware_rebuilt_for_recovery':False,
            'old_native_tests_retained':17,'unsafe_compile_guard_tests_retained':6,
            'esptool_481_compatibility':'OFFICIAL_SOURCE_REVIEW_PYTHON_GE_3_7_WINDOWS_3_11_SUPPORTED',
            'esptool_481_installed_by_agent':False,'hardware_read_attempts_by_agent':0,
            'flash_plan_cli_fix':'V4_Underscore_Options_V5_Hyphen_Options',
            'flash_plan_new_gate':'REQUIRE_VERIFIED_CONTIGUOUS_16MB_TWO_PASS_RECEIPT_AND_MATCHING_SHA_RANGES',
            'full16MB_hardware_backup':'NOT_VERIFIED_OWNER_REPORTS_INCOMPLETE','app_flash_conditions_met':False,
            'jetson_old_probes_accessed_or_modified':False,'jetson_backup_inventory':'PENDING_OWNER_READONLY_OUTPUT',
            'current_hx711_ram':'UNKNOWN_AFTER_ROM_RESETS','servo':'LOCKED','pump':'LOCKED',
            'production_source_changed':False,'accepted_rc':'PASS_UNCHANGED','physical_pass':False,
            'next_user_step':'SEE_EXECUTION_OWNER_STATE_HOLD_BACKUP_A' if (KIT/'execution/OWNER_STATE.json').exists() else 'READ_ONLY_INVENTORY_OF_EXISTING_BACKUP_DIR_AND_BRIDGE_STATES_ONLY',
            'stop_after_preparation':True}
        (KIT/'recovery/result.json').write_text(json.dumps(recovery,indent=2)+'\n',encoding='utf-8')
        if completed_pair:
            recovery.update(full16MB_hardware_backup='PASS_DIRECT_AB_FILE_INTEGRITY',
                jetson_backup_inventory='OLD_PROBES_PRESERVED_COMPARISON_NOT_VERIFIED',
                next_user_step='SEE_WEB_HARDWARE_HANDOFF_COMPLETED_AB_NO_THIRD_READ_OR_OLD_EXITCODE')
            (KIT/'recovery/result.json').write_text(json.dumps(recovery,indent=2)+'\n',encoding='utf-8')
    if (KIT/'execution/OWNER_STATE.json').exists():
        owner=read(KIT/'execution/OWNER_STATE.json')
        prepared={'kind':'PHYSICAL_ACCEPTANCE_EXECUTION_PREPARATION_RESULT','completed_at':result['completed_at'],
            'software_preparation':'READY_OFFLINE','hardware_execution_performed':False,
            'backup_A_state':'OWNER_LAST_REPORTED_RUNNING_NOT_POLLED_NO_COMPLETION_RECEIVED',
            'active_backup_file_accessed':False,'processes_interfered_with':False,'COM8_opened':False,
            'bridge_started_or_restarted':False,'firmware_rebuilt_or_changed':False,
            'production_source_or_release_changed':False,'accepted_rc_integrity':'PASS_UNCHANGED',
            'focused_tools_tests_passed':tools['python_tests'],'all_physical_gates_approved':False,
            'backup_AB_consistency':'NOT_VERIFIED','actual_running_boot_bank':'NOT_VERIFIED',
            'ECHO_voltage_gate':'NOT_VERIFIED','APP_flash_allowed_now':False,
            'HX711_static_physical_acceptance':'PASS_OWNER_ACCEPTED','HX711_retest_required':False,
            'HX711_persistence':'NOT_VERIFIED','HX711_closed_loop_35g':'NOT_VERIFIED',
            'primary_checklist':'PHYSICAL_EXECUTION_CHECKLIST.md','owner_state':'execution/OWNER_STATE.json',
            'next_user_action':owner['first_owner_step'],'stop_after_preparation':True}
        (KIT/'execution/result.json').write_text(json.dumps(prepared,indent=2)+'\n',encoding='utf-8')
        if completed_pair:
            prepared.update(backup_A_state='COMPLETED_OWNER_CONFIRMED_DIRECT_FILE_HASH',backup_AB_consistency='PASS',
                next_user_action=owner['first_owner_step'],third_read_required=False,old_exitcode_requested=False)
            (KIT/'execution/result.json').write_text(json.dumps(prepared,indent=2)+'\n',encoding='utf-8')
    if (KIT/'web_hardware/result.json').exists():
        web=read(KIT/'web_hardware/result.json');review=read(KIT/'web_hardware/backup_and_contract_review.json')
        parser=read(KIT/'web_hardware/native_parser_result.json')
        assert parser['OFFLINE_CPP14_JSONC_TEST_PASS'] is True and parser['parser_test_groups']==12
        assert 'checks=17' in parser['session_stdout'] and parser['ARM64_NATIVE_TEST_PASS'] is False
        assert parser['ARM64_R1_RETEST']=='NOT_RUN' and parser['kit_revision']=='GCC75_R1'
        assert web['native_parser_evidence']==parser,'stale Web native parser evidence'
        roi=web['food_roi_evidence']
        assert roi['FOOD_ROI_OFFLINE_PASS'] is True and roi['baseline_candidate_byte_identical_observations'] is True
        assert roi['after_food_roi_sha256']==sha(KIT/'web_hardware/bridge_candidate/food_roi.h')
        assert roi['test_driver_sha256']==sha(KIT/'web_hardware/bridge_candidate/test_food_roi.cpp')
        from verify_manifest import verify as verify_baseline
        assert verify_baseline(KIT/'web_hardware/gcc75_fix/baseline')['manifest_sha256']=='7dd06be68b089a62c30ff642c5479a8ff50a948eac02363faa330ec72d987da3'
        for name,digest in parser['source_sha256'].items():assert sha(KIT/'web_hardware/bridge_candidate'/name)==digest,'stale candidate native evidence '+name
        for name,meta in review['rollback_artifacts'].items():assert sha(KIT/'web_hardware'/name)==meta['sha256']
        source_reference=read(KIT/'web_hardware/bridge_source_reference.json')
        for name,meta in source_reference.items():assert sha(meta['source'])==meta['sha256'],'production bridge source changed '+name
        result.update(current_web_hardware_handoff='web_hardware/TELEMETRY_COMPATIBILITY_HANDOFF.md',
            current_execution_handoff='web_hardware/TELEMETRY_COMPATIBILITY_HANDOFF.md',
            first_owner_command='D:\\for_cat\\.venv\\Scripts\\python.exe -B D:\\for_cat\\HARDWARE_PHYSICAL_BRINGUP_20261029\\tools\\verify_manifest.py',
            backup_layout='PASS_ACTUAL_MD5_TABLE_AND_IMAGE_CHECKSUMS',
            backup_ota_selection_candidate='APP0_AT_0x10000_STANDARD_IDF_METADATA',
            runtime_boot_bank='NOT_VERIFIED',rollback_local_artifact='PASS_820C_REFERENCE_IMAGE',
            rollback_on_hardware='NOT_VERIFIED',web_hardware_backend_tests=web['backend_tests'],
            web_hardware_flutter_tests=web['flutter_tests'],web_hardware_flutter_analyze=web['flutter_analyze'],
            bridge_candidate_native_compile=web['bridge_candidate_native_compile'],
            kit_revision='GCC75_R1',OFFLINE_CPP14_JSONC_TEST_PASS=True,ARM64_NATIVE_TEST_PASS=False,
            ARM64_R1_RETEST='NOT_RUN',latest_owner_ARM64_attempt='FAIL_GCC75_MISLEADING_INDENTATION',
            gcc75_fix_handoff='web_hardware/gcc75_fix/ARM64_GCC75_R1_HANDOFF.md',
            food_roi_groups=web['food_roi_evidence']['groups'],food_roi_checks=web['food_roi_evidence']['checks'],
            food_roi_differential_cases=web['food_roi_evidence']['differential_cases'],
            native_parser_test_groups=12,native_diagnostic_session_checks=17,
            pre_flash_gate_review='web_hardware/PRE_FLASH_GATES.json',
            live_buzzer_web_test='BLOCKED_CURRENT_FIRMWARE_AND_RPC_CAPABILITY',
            current_web_hardware_stage='OFFLINE_PREPARATION_WITH_EXPLICIT_LIVE_BLOCKERS',APP_flash_allowed_now=False)
        (KIT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    excluded={'manifest.json','manifest.sha256','SHA256SUMS'}
    excluded_dirs={'.pio','.dart_tool','build','__pycache__','.pytest_cache','.git','evidence',
        'conditional_artifacts','conditional_logs','recovery_workspace','native_tooling','json_c_source',
        'native_jsonc_build','native_jsonc_install','native_parser'}
    files={}
    for parent,directories,names in os.walk(KIT):
        relative=Path(parent).relative_to(KIT)
        directories[:]=sorted(d for d in directories if d not in excluded_dirs and
            not (relative==Path('web_hardware') and d.startswith('native_arm64_')))
        for name in sorted(names):
            path=Path(parent)/name;rel=path.relative_to(KIT)
            if path.name.startswith('.flutter-plugins'):continue
            if path.is_file() and path.suffix not in ('.exe','.pyc') and rel.as_posix() not in excluded:
                files[rel.as_posix()]={'sha256':sha(path),'bytes':path.stat().st_size}
    manifest={'kind':'FORCAT_PHYSICAL_KIT_INTEGRITY_V1','scope':'OFFLINE_SOURCE_ARTIFACTS_AND_SOFTWARE_EVIDENCE_NOT_PHYSICAL_ACCEPTANCE',
        'excluded_generated_directories':sorted(excluded_dirs)+['web_hardware/native_arm64_* owner runs'],
        'files':dict(sorted(files.items()))}
    (KIT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (KIT/'manifest.sha256').write_text(sha(KIT/'manifest.json')+'\n')
    (KIT/'SHA256SUMS').write_text(''.join(meta['sha256']+'  '+name+'\n' for name,meta in sorted(files.items())))
    from verify_manifest import verify
    verify(KIT)
    print(json.dumps({'HARDWARE_TEST_KIT_OFFLINE_READY':'YES','python_tests':tools['python_tests'],'native_cases':17,'manifest_sha256':sha(KIT/'manifest.json'),'physical_pass':False}))
if __name__=='__main__':main()
