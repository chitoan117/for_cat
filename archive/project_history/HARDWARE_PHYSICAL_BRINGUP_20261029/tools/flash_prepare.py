"""OFFLINE plan generator only. Never executes esptool, opens serial or flashes.
APP-only write plan is withheld until a full backup/layout/boot-bank/owner review.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from image_layout import FLASH_SIZE,sha,partitions,image_header,app_partition,load_full_backup

KIT=Path(__file__).resolve().parents[1]
def artifact(profile,observation=None):
    conditional=profile in ('diag_pump_bench_active_high','diag_pump_bench_active_low')
    if conditional:
        from build_windows import pump_variant
        expected=pump_variant(0 if profile.endswith('high') else 1,observation)
        if expected!=profile:raise ValueError('pump polarity/evidence mismatch')
    path=KIT/('conditional_artifacts' if conditional else 'artifacts')/profile
    data=json.loads((path/'layout.json').read_text(encoding='utf-8'))
    for name,meta in data['artifacts'].items():
        p=path/name
        if sha(p)!=meta['sha256'] or p.stat().st_size!=meta['bytes']:raise ValueError('artifact integrity mismatch')
    return path,data
def make_plan(profile,port,backup,boot_offset=None,ram_ack=False,power_ack=False,rollback_path=None,style='v5',observation=None,tool_command=None,backup_receipt=None,running_partition_review=None):
    folder,layout=artifact(profile,observation)
    if tool_command is None:
        from build_windows import PIO,ESPTOOL
        tool_command=[str(PIO),str(ESPTOOL)] if os.name=='nt' and PIO.is_file() and ESPTOOL.is_file() else [sys.executable,'-m','esptool']
    base=list(tool_command)+['--chip','esp32s3','--port',port]
    names={'read':'read-flash','write':'write-flash','verify':'verify-flash','id':'flash-id'} if style=='v5' else {'read':'read_flash','write':'write_flash','verify':'verify_flash','id':'flash_id'}
    flash_options=['--flash-mode','keep','--flash-freq','keep','--flash-size','keep'] if style=='v5' else ['--flash_mode','keep','--flash_freq','keep','--flash_size','keep']
    result={'mode':'PLAN_ONLY_NO_EXECUTION','profile':profile,'physical_pass':False,'flash_executed':False,
        'application_offset_from_build':layout['app_offset'],'partition_table_offset_from_build':layout['partition_table_offset'],
        'bootloader_offset_from_build':layout['bootloader_offset'],'full_backup_command':base+[names['read'],'0x0',hex(FLASH_SIZE),str(backup)],
        'flash_identity_command':base+[names['id']],'write_plan_available':False,
        'warning':'ROM/esptool reset or unplug loses HX711 RAM calibration; save current status/log FIRST. No erase_flash. Do not flash factory/bootloader/partition images.',
        'bridge_exclusivity':'Stop the correct bridge before ROM/serial work and restore ORIGINAL state in shell trap/finally. Windows COM must be exclusively owned.'}
    backup=Path(backup)
    if not backup.is_file():result['blocker']='FULL_DEVICE_BACKUP_MISSING';return result
    if backup_receipt is None:result['blocker']='VERIFIED_TWO_PASS_BACKUP_RECEIPT_REQUIRED_SIZE_ALONE_IS_NOT_PROOF';return result
    from backup_recovery import validate_receipt
    validate_receipt(backup,backup_receipt)
    data,old_table=load_full_backup(backup,layout['partition_table_offset'])
    if old_table!=layout['partitions']:result['blocker']='PARTITION_LAYOUT_MISMATCH_OWNER_REVIEW_NO_AUTOMATIC_FULL_FLASH';return result
    if boot_offset is None or boot_offset!=layout['app_offset']:result['blocker']='ACTIVE_BOOT_BANK_NOT_CONFIRMED_FROM_OWNER_BOOT_EVIDENCE';return result
    if not ram_ack or not power_ack:result['blocker']='OWNER_RAM_LOSS_AND_EXTERNAL_ACTUATOR_POWER_ISOLATION_ACK_REQUIRED';return result
    if running_partition_review is None:result['blocker']='REVIEWED_RUNNING_PARTITION_EVIDENCE_REQUIRED_OTA_CANDIDATE_IS_NOT_PROOF';return result
    from physical_acceptance import validate_boot_review
    validate_boot_review(backup,running_partition_review,boot_offset,layout['partition_table_offset'])
    app=app_partition(old_table,boot_offset);image_header(data[boot_offset:boot_offset+24])
    result.update(full_backup_sha256=sha(backup),active_boot_bank_authority='OWNER_DECLARED_BOOT_LOG_NOT_AUTO_DETECTED',
        write_plan_available=True,physical_result='NOT_VERIFIED',app_region_size=app['size'],
        application_write_command=base+[names['write']]+flash_options+[hex(boot_offset),str(folder/'firmware.bin')],
        application_verify_command=base+[names['verify'],hex(boot_offset),str(folder/'firmware.bin')],
        nvs_or_partition_write_planned=False,automatic_tare_or_nvs_write=False)
    if rollback_path:
        rollback_path=Path(rollback_path)
        with rollback_path.open('xb') as f:f.write(data[boot_offset:boot_offset+app['size']])
        result.update(rollback_app_sha256=sha(rollback_path),rollback_extract=str(rollback_path),
            rollback_command=base+[names['write'],hex(boot_offset),str(rollback_path)],
            rollback_verify_command=base+[names['verify'],hex(boot_offset),str(rollback_path)])
    else:result['rollback_note']='Use --extract-rollback-path NEW_FILE before any app write; extraction is local only and preserves NVS on app restore.'
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=('diag_four_ultrasonic','diag_dog_buzzer','diag_servo_bench','diag_pump_bench','diag_pump_bench_active_high','diag_pump_bench_active_low'),default='diag_four_ultrasonic')
    p.add_argument('--port',required=True);p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--backup-receipt',type=Path)
    p.add_argument('--running-partition-review',type=Path)
    p.add_argument('--boot-app-offset',type=lambda v:int(v,0));p.add_argument('--ram-loss-ack',action='store_true')
    p.add_argument('--external-actuator-power-isolated',action='store_true');p.add_argument('--extract-rollback-path',type=Path)
    p.add_argument('--pump-observation',type=Path)
    p.add_argument('--esptool-python');p.add_argument('--esptool-script',type=Path)
    p.add_argument('--esptool-style',choices=('v4','v5'),default='v5');a=p.parse_args()
    tool=None
    if a.esptool_python or a.esptool_script:tool=[a.esptool_python or sys.executable]+([str(a.esptool_script)] if a.esptool_script else ['-m','esptool'])
    print(json.dumps(make_plan(a.profile,a.port,a.backup,a.boot_app_offset,a.ram_loss_ack,a.external_actuator_power_isolated,a.extract_rollback_path,a.esptool_style,a.pump_observation,tool,a.backup_receipt,a.running_partition_review),indent=2))
if __name__=='__main__':main()
