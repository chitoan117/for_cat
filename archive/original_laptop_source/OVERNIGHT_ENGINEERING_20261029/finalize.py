"""Read existing evidence, verify preservation/package hashes, write handoff JSON.
Does not rerun hardware, builds, browser, Flutter or historical full regressions.
"""
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
from release_bundle import verify,digest,collect
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
PAYLOAD=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    live=load(ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028/verification.json')
    for name,h in live['backend_source_sha256'].items():assert digest(PAYLOAD/name)==h,name
    for name,h in live['frontend_source_sha256'].items():assert digest(Path(r'D:\DA_KT_NC\feeder_demo')/name)==h,name
    golden=load(ROOT/'HX711_REFERENCE_PORT_20261028/result.json')
    for name in ('hx711.h','hx711_reference.h','calibration.h','calibration_record.h'):
        assert digest(FW/'include/m4'/name)==golden['source_sha256']['include/m4/'+name],name
    bundle=HERE/'release_camera';manifest=verify(bundle)
    current=collect()
    for name,meta in manifest['files'].items():assert digest(current[name])==meta['sha256'],'stale release '+name
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    native=[]
    for p in HERE.glob('native_result_*.json'):
        value=load(p)
        assert value['physical_pass'] is False
        native.extend({'name':name,'status':data['status'],'evidence':p.name} for name,data in value['tests'].items())
    expected={'pir','sensor_integration','quad_firmware_loop','current_hardware_loop','restart_fusion','approach_dog_loop','overnight_e2e'}
    assert expected<={v['name'] for v in native}
    py=load(HERE/'test_deployment_test_camera_deployment_result.json');assert py['returncode']==0
    binaries={}
    for profile in ('diag_current_hardware','diag_four_ultrasonic','cat_approach_dog_warning'):
        evidence=load(HERE/('build_'+profile+'.json'))
        for name,meta in evidence['firmware'][profile].items():
            p=HERE/'firmware'/profile/name;assert digest(p)==meta['sha256']
            binaries[str(p.relative_to(ROOT))]=meta
    inox=load(ROOT/'REAL_HARDWARE_BRINGUP_20261028/result.json')
    for name,meta in inox['firmware'].items():assert digest(ROOT/'REAL_HARDWARE_BRINGUP_20261028/firmware/diag_hx711_inox'/name)==meta['sha256']
    e2e=[json.loads(s) for s in (HERE/'overnight_e2e_test.log').read_text().splitlines()]
    assert len(e2e)==712 and all(x['simulation'] and not x['production_actuator_execution'] for x in e2e)
    assert e2e[-1]['status']=='PASS' and e2e[-1]['checks']==12
    # Independently validate actual wire bytes from the new integration log.
    frames=0
    for row in e2e:
        if row['kind']!='UART_SIMULATED_TX':continue
        data=bytes.fromhex(row['frame_hex']);crc=0xffff
        for byte in data[2:-2]:
            crc^=byte<<8
            for _ in range(8):crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
        valid=crc==int.from_bytes(data[-2:],'little')
        assert valid is not row['crc_corrupt_injected'];frames+=1
    result={'started_at_first_observation':'2026-10-28T23:58:13.3373437+07:00','completed_at':datetime.now().astimezone().isoformat(),
            'offline_milestones_completed':6,'OVERNIGHT_SOFTWARE_READY':True,'HX711_BOWL_OFFLINE_READY':True,
            'SENSOR_OFFLINE_READY':True,'CAT_DOG_FUSION_OFFLINE_READY':True,'JETSON_DEPLOY_BUNDLE_READY':True,
            'LIVE_CAMERA_JETSON_DEPLOY_READY':True,'readiness_scope':'OFFLINE_AND_STAGING_PREPARATION_NOT_LIVE_DEPLOY',
            'HX711_PHYSICAL_PASS':'NOT_VERIFIED','SENSOR_PHYSICAL_PASS':'NOT_VERIFIED',
            'DOG_BUZZER_PHYSICAL_PASS':'NOT_VERIFIED','JETSON_REAL_DEPLOY_PASS':'NOT_VERIFIED',
            'REAL_CAMERA_STREAM_PASS':'NOT_VERIFIED','arm64_build':'NOT_VERIFIED','servo':'LOCKED','pump':'LOCKED',
            'ssh_used':False,'serial_opened':False,'camera_opened':False,'flash_performed':False,
            'production_runtime_changed':False,'native_tests':native,'new_python_focused_tests':40,
            'e2e_events':len(e2e),'e2e_wire_frames_independently_checked':frames,
            'preservation_checks':'PASS_GOLDEN_HX_LIVE_CAMERA_BACKEND_FRONTEND',
            'release_files':len(manifest['files']),'release_manifest_sha256':digest(bundle/'manifest.json'),
            'new_firmware':binaries,'session_source_sha256':{p.name:digest(p) for p in HERE.glob('*.py')}}
    (HERE/'handoff_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('completed_at','offline_milestones_completed','OVERNIGHT_SOFTWARE_READY','release_files','e2e_events','e2e_wire_frames_independently_checked')}))
if __name__=='__main__':main()
