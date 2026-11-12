"""OFFLINE only. No subprocess/serial/service execution, even after approval.
With incomplete gates, emits blockers and withholds executable flash arguments.
"""
from __future__ import print_function
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import struct
import sys
import readiness as r

GATES=('separate_flash_approval','board_and_current_boot_bound',
       'security_policy_and_both_images_reviewed','four_echo_measurements_reviewed',
       'external_load_power_isolated','HX711_RAM_loss_accepted',
       'serial_exclusive_and_ROM_ready','ROM_no_stub_write_verify_path_reviewed',
       'recovery_route_and_original_bridge_handback_reviewed')
def blockers(v,now=None):
    problems=[]
    if v.get('scope')!='OFFLINE_APP_ONLY_PLAN_AFTER_SEPARATE_FLASH_APPROVAL' or not v.get('approved_by'):problems.append('SEPARATE_REVIEW_REQUIRED')
    for key in GATES:
        if v.get('gates',{}).get(key) is not True:problems.append(key)
    try:
        expires=datetime.strptime(v['valid_until_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        if not 0<(expires-(now or datetime.now(timezone.utc))).total_seconds()<=86400:problems.append('APPROVAL_EXPIRED_OR_OUT_OF_SCOPE')
    except (KeyError,ValueError):problems.append('VALID_EXPIRY_REQUIRED')
    if type(v.get('actual_running_offset')) is not int or v['actual_running_offset']!=0x10000:problems.append('ACTUAL_BANK_NOT_CONFIRMED_APP0_NO_OFFSET_GUESS')
    sec=v.get('security',{})
    for key in ('secure_boot_enabled','flash_encryption_enabled','download_mode_disabled','secure_download_enabled'):
        if sec.get(key) is not False:problems.append('UNSUPPORTED_OR_UNKNOWN_SECURITY_POLICY_'+key)
    if type(sec.get('secure_version_counter')) is not int or sec['secure_version_counter']!=0:problems.append('ANTIROLLBACK_NOT_COMPATIBLE_WITH_VERSION0_OR_UNKNOWN')
    if v.get('tool_version')!='4.8.1' or not r.regular(v.get('tool_python','')):problems.append('REVIEWED_4_8_1_EXECUTOR_REQUIRED')
    port=v.get('port','')
    if not (re.match(r'^COM[1-9][0-9]*$',port,re.I) or port==r.BYID):problems.append('ACTUAL_EXECUTOR_PORT_REQUIRED')
    evidence=v.get('evidence_files_sha256',{})
    if len(evidence)<2:problems.append('BOUND_BOOT_AND_SECURITY_EVIDENCE_REQUIRED')
    for path,digest in evidence.items():
        if not r.regular(path) or r.sha(path)!=digest:problems.append('EVIDENCE_CHANGED_OR_MISSING:'+path)
    return problems

def descriptor_version(path):
    raw=Path(path).read_bytes()
    if len(raw)<40 or struct.unpack_from('<I',raw,32)[0]!=0xabcd5432:raise ValueError('known ESP app descriptor at first DROM segment required')
    return struct.unpack_from('<I',raw,36)[0]

def plan(v):
    why=blockers(v)
    if why:return {'mode':'PLAN_ONLY','APP_FLASH':'NO_GO','blockers':why,'write_argv_available':False}
    sensor=r.KIT/'artifacts/diag_four_ultrasonic/firmware.bin'
    old=r.KIT/'web_hardware/rollback_original_app_00010000.bin'
    if r.sha(sensor)!=r.SENSOR_SHA or r.sha(old)!=r.ROLLBACK_SHA:raise ValueError('artifact identity mismatch')
    if descriptor_version(sensor)!=0 or descriptor_version(old)!=0:raise ValueError('image secure-version outside reviewed version0 policy')
    sys.path.insert(0,str(r.KIT/'tools'))
    from flash_prepare import make_plan
    base=[v['tool_python'],'-B','-m','esptool','--chip','esp32s3','--port',v['port'],
          '--baud','115200','--before','no_reset','--after','no_reset','--no-stub']
    # Existing validator binds the actual boot review to backup/table/image layout.
    result=make_plan('diag_four_ultrasonic',v['port'],v['backup'],v['actual_running_offset'],
        True,True,None,'v4',None,[v['tool_python'],'-B','-m','esptool',
        '--baud','115200','--before','no_reset','--after','no_reset','--no-stub'],
        v['backup_receipt'],v['running_partition_review'])
    if not result.get('write_plan_available'):return {'mode':'PLAN_ONLY','APP_FLASH':'NO_GO','blockers':[result.get('blocker')],'write_argv_available':False}
    flags=['--flash_mode','keep','--flash_freq','keep','--flash_size','keep']
    offset=hex(v['actual_running_offset'])
    return {'mode':'OFFLINE_REVIEWED_ARGV_NEVER_EXECUTED','write_argv_available':True,
        'flash_executed':False,'security_branch':'REVIEWED_UNENCRYPTED_UNSIGNED_UNRESTRICTED_ONLY',
        'write_argv':base+['write_flash','--no-compress']+flags+[offset,str(sensor)],
        'verify_argv':base+['verify_flash',offset,str(sensor)],
        'rollback_argv':base+['write_flash','--no-compress']+flags+[offset,str(old)],
        'rollback_verify_argv':base+['verify_flash',offset,str(old)],
        'reset':'NO_AUTOMATIC_RESET; approved normal boot/capture/handback is a separate owner action',
        'physical_pass':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    result=plan(json.loads(a.review.read_text()) if a.review else {})
    if a.output:r.write_new(a.output,result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
