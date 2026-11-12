"""One-shot R2 source consolidation. No deployment or baseline mutation."""
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
OLD=ROOT/'OVERNIGHT_ENGINEERING_20261029/offline_continuation'
KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (HERE/'candidate').exists():raise ValueError('R2 candidate already exists; no overwrite')
    assert sha(OLD/'ARTIFACT_MANIFEST.json')=='c12fc0b7b748686b97eac013e2e60351eb22c254c767eaff121d013525628a54'
    for name,meta in json.loads((OLD/'ARTIFACT_MANIFEST.json').read_text())['files'].items():
        assert sha(OLD.parent/name)==meta['sha256'],'overnight artifact changed '+name
    assert sha(KIT/'manifest.json')=='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
    assert sha(KIT/'web_hardware/gcc75_fix/transfer_manifest.json')=='de20b028df9a63f73a7b316d527ac980fc4d336120a40266c8935eccf8cf0322'
    records={}
    def take(source,rel):
        target=HERE/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(source.read_bytes())
        records[rel]={'source':str(source),'sha256':sha(source)}
    bridge=('telemetry.h','ultrasonic_telemetry.h','diagnostic_session.h','feed_policy.h',
            'decision_logic.h','approach_fusion.h','food_roi.h','roi_species.h','owner_behavior.h',
            'esp32_bridge.cpp','parser_replay.cpp','test_session.cpp','test_food_roi.cpp')
    for name in bridge:take(OLD/'candidate/bridge'/name,'candidate/bridge/'+name)
    for name in ('dispense_bench.h','servo_bench.h'):
        take(OLD/'candidate/firmware/include/m4'/name,'candidate/firmware/include/m4/'+name)
    take(KIT/'firmware/include/dog_warning_protocol.h','candidate/protocol/dog_warning_protocol.h')
    take(OLD/'candidate/diagnostics.py','candidate/diagnostics.py')
    for name in ('hardware_diagnostics_panel.dart','offline_history_panel.dart','pubspec.yaml','test/continuation_test.dart'):
        take(OLD/'candidate/flutter'/name,'candidate/flutter/'+name)
    for name in ('logic_tests.cpp','timeline_probe.cpp','test_integration.py'):take(OLD/'tests'/name,'tests/'+name)
    for name in ('synthetic_wire.json','synthetic_wire.jsonl'):take(OLD/'fixtures'/name,'fixtures/'+name)
    take(KIT/'test_output/quad_firmware_loop_test.log','fixtures/r1_quad_reports.log')
    (HERE/'SOURCE_PROVENANCE.json').write_text(json.dumps({'revision':'GCC75_R2','inputs':records,
        'R1_ARM64':'OWNER_CONFIRMED_PASS','R2_ARM64_NATIVE_TEST_PASS':'NOT_RUN',
        'qualified_R1_manifest':sha(KIT/'manifest.json'),'overnight_manifest':sha(OLD/'ARTIFACT_MANIFEST.json')},indent=2)+'\n')
    print(json.dumps({'R2_sources_staged':len(records),'locked_inputs_changed':False}))
if __name__=='__main__':main()
