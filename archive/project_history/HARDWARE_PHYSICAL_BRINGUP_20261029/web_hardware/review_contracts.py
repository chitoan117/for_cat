"""File-only review: no target process, camera, UART or service operations."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;KIT=HERE.parent
sys.path.insert(0,str(KIT/'tools'))
from physical_acceptance import inspect_contents
from image_layout import sha
from completed_backup_pair import validate_pair
from backup_recovery import new_json
EXPECTED='56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16'
def main():
    pair=json.loads((HERE/'accepted_backup_pair.json').read_text())
    validate_pair(pair['files'][0]['file'],pair['files'][1]['file'],EXPECTED)
    data=Path(pair['files'][0]['file']).read_bytes();analysis=inspect_contents(data,EXPECTED)
    layout=json.loads((KIT/'artifacts/diag_four_ultrasonic/layout.json').read_text())
    candidate=analysis['partition_candidates'];artifacts={}
    if len(candidate)==1:
        t=candidate[0];valid=[x for x in t['ota_copies'] if x['select_record_usable']]
        selected=max(valid,key=lambda x:x['ota_seq']) if valid else None
        for p in t['apps']:
            start=p['offset'];length=p['image'].get('image_bytes')
            p['partition_all_ff']=all(b==255 for b in data[start:start+p['size']])
            if length:
                p['used_image_sha256']=__import__('hashlib').sha256(data[start:start+length]).hexdigest()
                target=HERE/('rollback_original_app_%08x.bin'%start)
                with target.open('xb') as out:out.write(data[start:start+length])
                artifacts[str(target.name)]={'bytes':length,'sha256':sha(target),'offset':start,'scope':'ORIGINAL_IMAGE_LOCAL_RECOVERY_ONLY_NOT_FLASH_AUTHORIZATION'}
        boot_len=analysis['bootloader_at_rom_s3_offset0'].get('image_bytes')
        boot_sha=__import__('hashlib').sha256(data[:boot_len]).hexdigest() if boot_len else None
        matches=t['table_offset']==layout['partition_table_offset'] and t['partitions']==layout['partitions']
    else:selected=None;boot_sha=None;matches=False
    firmware_lines=[s for s in (KIT/'test_output/quad_firmware_loop_test.log').read_text().splitlines() if s.startswith('{')]
    line_lengths=[len(s.encode()) for s in firmware_lines]
    report={'backup_AB_file_integrity':'PASS','sha256':EXPECTED,'bytes_each':16777216,
        'actual_flash_analysis':analysis,'layout_matches_new_sensor_build':matches,
        'bootloader_image_sha256':boot_sha,'boot_selection_from_ota_standard_idf_candidate':selected,
        'runtime_boot_bank':'NOT_VERIFIED_NO_RUNNING_PARTITION_LOG_IN_THIS_ANALYSIS',
        'rollback_local_image_extraction':'PASS' if artifacts else 'NOT_VERIFIED','rollback_artifacts':artifacts,
        'rollback_on_hardware':'NOT_VERIFIED','flash_authorized':False,
        'compatibility':{'kit_json_line_bytes':line_lengths,'current_bridge_line_limit':4096,
            'kit_fits_current_bridge_line_bound':all(n<=4096 for n in line_lengths),
            'firmware_sensor_mode':'diag_current_hardware','current_backed_up_app':'HX711_REFERENCE_known820cdeec_image',
            'PIR_qualified_fields_forwarded_by_current_bridge':False,'HX_firmware_grams_forwarded_by_current_bridge':False,
            'JSN_geometry_level_api_available':False,'manual_buzzer_endpoint_available':False,
            'sensor_image_has_buzzer_GPIO2_capability':False},'hardware_operations_performed':False}
    new_json(HERE/'backup_and_contract_review.json',report)
    print(json.dumps({'backup_AB':'PASS','table_matches':matches,'ota_candidate':selected,
        'runtime_bank':report['runtime_boot_bank'],'rollback':artifacts,'compatibility':report['compatibility']},indent=2))
if __name__=='__main__':main()
