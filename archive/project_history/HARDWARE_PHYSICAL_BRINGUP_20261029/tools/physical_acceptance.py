"""FILE-ONLY physical-execution preparation. No serial or subprocess operations.
No process enumeration, polling, reset, port/service operation or flash execution.
record() refuses BEFORE touching any backup path until owner reports completion.
"""
import argparse
import binascii
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from backup_recovery import mac,new_json,read_json,validate_receipt
from image_layout import FLASH_SIZE,sha,partitions,image_header

RECORD_KIND='FORCAT_COMPLETED_EXTERNAL_READ_V1'
def stable_hash(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('regular completed backup required')
    before=path.stat();digest=sha(path);after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('backup changed while hashing: BLOCKED')
    return after.st_size,digest
def record(label,backup,log,output,exit_code,reader_finished=False,device_id=None,transport='ROM'):
    # This ordering is deliberate: do not stat/hash/open an active .partial file.
    if not reader_finished or type(exit_code) is not int or exit_code!=0:raise ValueError('BLOCKED: reader must have ended with known esptool exit0')
    if label not in ('A','B') or transport not in ('ROM','STUB'):raise ValueError('pass/transport')
    device_id=mac(device_id);backup=Path(backup).resolve();log=Path(log).resolve();output=Path(output)
    if output.exists():raise ValueError('NEW completion record required; preserve all old evidence')
    text=log.read_text(encoding='utf-8',errors='replace')
    if not re.search(r'(?:esptool(?:\.py)?\s+v)?4\.8\.1\b',text) or 'ESP32-S3' not in text:raise ValueError('complete log must identify esptool4.8.1/S3')
    ids={m.lower() for m in re.findall(r'\bMAC:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})',text)}
    if ids!={device_id}:raise ValueError('log/device MAC mismatch')
    if re.search(r'A fatal error|Invalid head of packet|CRC error|Traceback',text,re.I):raise ValueError('failed read log cannot be accepted')
    if 'FULL_BACKUP_READ_PASS' not in text and not re.search(r'Read\s+16777216\s+bytes\s+at\s+0x0+\b',text,re.I):raise ValueError('full-read completion evidence missing')
    if transport=='ROM' and re.search(r'Running stub|Stub running',text,re.I):raise ValueError('ROM declaration conflicts with log')
    size,digest=stable_hash(backup)
    if size!=FLASH_SIZE:raise ValueError('BLOCKED: exact16777216bytes required; no padding')
    result={'kind':RECORD_KIND,'label':label,'backup':str(backup),'log':str(log),'log_sha256':sha(log),
        'bytes':size,'sha256':digest,'device_id':device_id,'exit_code':exit_code,'reader_finished':True,
        'esptool_version':'4.8.1','transport':transport,'transport_authority':'OWNER_COMMAND_REVIEW_PLUS_LOG',
        'recorded_utc':datetime.now(timezone.utc).isoformat(),'physical_pass':False,'flash_authorized':False}
    new_json(output,result);return result
def completed(path):
    r=read_json(path)
    if r.get('kind')!=RECORD_KIND or r.get('reader_finished') is not True or type(r.get('exit_code')) is not int or r['exit_code']!=0 or r.get('esptool_version')!='4.8.1':raise ValueError('completed read record missing/invalid')
    mac(r['device_id']);size,digest=stable_hash(r['backup'])
    if size!=FLASH_SIZE or size!=r['bytes'] or digest!=r['sha256'] or sha(r['log'])!=r['log_sha256']:raise ValueError('completed evidence changed')
    return r
def plan_b(record_a,new_backup,tool_python,port='COM8'):
    a=completed(record_a);new_backup=Path(new_backup).resolve()
    if new_backup.exists() or str(new_backup)==a['backup']:raise ValueError('NEW B output, never overwrite A')
    if not re.fullmatch(r'COM[1-9][0-9]*',port,re.I):raise ValueError('explicit owner-reviewed COM required')
    argv=[str(tool_python),'-B','-m','esptool','--chip','esp32s3','--port',port,'--baud','115200',
          '--before','no_reset','--after','no_reset']
    if a['transport']=='ROM':argv+=['--no-stub']
    argv+=['read_flash','--flash_size','16MB','0x0',hex(FLASH_SIZE),str(new_backup)]
    return {'mode':'PLAN_ONLY_NO_DEVICE_OPEN','argv':argv,'device_id':a['device_id'],'transport':a['transport'],
        'owner_rom_power_usb_review_required':True,'physical_pass':False,'execution_implemented':False}
def compare_pair(record_a,record_b,output,owner_continuity_reviewed=False):
    if not owner_continuity_reviewed:raise ValueError('BLOCKED: owner must review same-board ROM continuity/app writes')
    a=completed(record_a);b=completed(record_b)
    if a['label']!='A' or b['label']!='B' or a['device_id']!=b['device_id'] or a['transport']!=b['transport']:raise ValueError('BLOCKED: independent A/B device/transport mismatch')
    if os.path.samefile(a['backup'],b['backup']) or os.path.samefile(a['log'],b['log']):raise ValueError('A/B must be independent files AND read logs, not same file/hardlink')
    if a['sha256']!=b['sha256']:raise ValueError('BLOCKED: full16MB A/B SHA256 mismatch')
    result={'kind':'FORCAT_VERIFIED_FLASH_BACKUP_V1','bytes':FLASH_SIZE,'sha256':a['sha256'],'device_id':a['device_id'],
        'coverage_bytes':FLASH_SIZE,'contiguous_from_zero':True,'two_independent_passes_match':True,
        'ranges':[{'offset':0,'size':FLASH_SIZE,'sha256':a['sha256'],'pass_a':a['backup'],'pass_b':b['backup']}],
        'rom_continuity':'OWNER_REVIEWED','transport':a['transport'],'completed_records':[str(record_a),str(record_b)],
        'physical_pass':False,'flash_write_authorized':False,'active_boot_bank':'NOT_VERIFIED'}
    validate_pair_candidate(a,result)
    new_json(output,result);return result
def validate_pair_candidate(a,receipt):
    if receipt['bytes']!=a['bytes'] or receipt['sha256']!=a['sha256']:raise ValueError('pair receipt inconsistency')
def compare_probes(backup,receipt,probe_manifest):
    validate_receipt(backup,receipt);spec=read_json(probe_manifest);results=[]
    for entry in spec.get('probes',[]):
        at=entry.get('offset');size=entry.get('bytes');path=Path(entry['file'])
        if type(at) is not int or type(size) is not int or at<0 or size<=0 or at+size>FLASH_SIZE:raise ValueError('probe offset/length must be explicit and bounded')
        if entry.get('read_exit_code')!=0 or entry.get('offset_source')!='OWNER_REVIEWED_COMMAND_LOG':raise ValueError('probe success/address cannot be inferred from filename')
        if path.stat().st_size!=size:raise ValueError('probe size mismatch')
        with Path(backup).open('rb') as f:f.seek(at);region=f.read(size)
        digest=hashlib.sha256(region).hexdigest();actual=sha(path)
        results.append({'file':str(path),'offset':at,'bytes':size,'probe_sha256':actual,'backup_region_sha256':digest,
                        'comparison':'MATCH' if digest==actual else 'MISMATCH_REVIEW_REQUIRED'})
    return {'probe_comparison':results,'any_mismatch':any(r['comparison']!='MATCH' for r in results),
        'old_files_modified':False,'flash_authorized':False,'physical_pass':False}
def image_details(data,start,limit):
    try:
        header=image_header(data[start:start+24]);end=start+24;checksum=0xef
        if not 1<=header['segments']<=16:raise ValueError('segment count')
        for _ in range(header['segments']):
            if end+8>limit:raise ValueError('short segment header')
            _,size=struct.unpack_from('<II',data,end);end+=8
            if end+size>limit:raise ValueError('segment exceeds image region')
            for byte in data[end:end+size]:checksum^=byte
            end+=size
        check_at=start+((end-start)|15)
        if check_at>=limit or data[check_at]!=checksum:raise ValueError('image checksum mismatch')
        hash_at=check_at+1;hash_appended=data[start+23]==1
        if hash_appended and (hash_at+32>limit or hashlib.sha256(data[start:hash_at]).digest()!=data[hash_at:hash_at+32]):raise ValueError('appended image SHA mismatch')
        return {**header,'image_integrity':'VALID_LOCAL_BYTES','image_bytes':hash_at-start+(32 if hash_appended else 0),
                'appended_hash':hash_appended,'secure_boot_signature_verified':False}
    except (ValueError,struct.error,IndexError) as e:return {'image_integrity':'UNVERIFIED_OR_INVALID','error':str(e)}
def inspect(backup,receipt):
    validate_receipt(backup,receipt)
    return inspect_contents(Path(backup).read_bytes(),sha(backup))
def inspect_contents(data,digest):
    if len(data)!=FLASH_SIZE:raise ValueError('full16MB local bytes required')
    tables=[]
    states={0:'NEW',1:'PENDING_VERIFY',2:'VALID',3:'INVALID',4:'ABORTED',0xffffffff:'UNDEFINED'}
    for at in range(0,FLASH_SIZE-4096+1,4096):
        if data[at:at+2]!=b'\xaa\x50':continue
        try:parts=partitions(data[at:at+4096])
        except (ValueError,UnicodeError):continue
        apps=[{**p,'image':image_details(data,p['offset'],p['offset']+p['size'])} for p in parts if p['type']==0]
        ota=[];slots=sorted([p for p in apps if 0x10<=p['subtype']<=0x1f],key=lambda p:p['subtype'])
        contiguous=bool(slots) and [p['subtype'] for p in slots]==list(range(0x10,0x10+len(slots)))
        for p in parts:
            if p['type']!=1 or p['subtype']!=0:continue
            for copy in (0,1):
                address=p['offset']+copy*4096
                if address+32>p['offset']+p['size']:continue
                raw=data[address:address+32];seq=struct.unpack_from('<I',raw)[0];state,crc=struct.unpack_from('<II',raw,24)
                expected=binascii.crc32(raw[:4],0xffffffff)&0xffffffff
                valid=seq!=0xffffffff and crc==expected and state not in (3,4)
                ota.append({'copy':copy,'offset':address,'ota_seq':seq,'ota_state':states.get(state,'UNKNOWN'),
                    'stored_crc':crc,'computed_crc':expected,'record_crc_valid':crc==expected,'select_record_usable':valid,
                    'sequence_mapped_candidate_offset':slots[((seq-1)&0xffffffff)%len(slots)]['offset'] if valid and contiguous else None})
        tables.append({'table_offset':at,'partitions':parts,'apps':apps,'ota_copies':ota})
    return {'full_backup_sha256':digest,'bootloader_at_rom_s3_offset0':image_details(data,0, min([p['table_offset'] for p in tables],default=0x8000)),
        'partition_candidates':tables,'active_boot_bank':'NOT_VERIFIED_REQUIRES_RUNNING_PARTITION_EVIDENCE',
        'note':'OTA sequence mapping is a candidate only: rollback/fallback/security/bootloader config may select differently.',
        'flash_authorized':False,'physical_pass':False}
def boot_gate(backup,receipt,evidence):
    analysis=inspect(backup,receipt);e=read_json(evidence)
    if e.get('backup_sha256')!=analysis['full_backup_sha256'] or e.get('evidence_kind')!='RUNNING_PARTITION_OBSERVATION' or not e.get('observer') or not e.get('log_file'):raise ValueError('BLOCKED: actual running-partition evidence bound to backup required')
    text=Path(e['log_file']).read_text(encoding='utf-8',errors='replace');offset=e.get('running_app_offset')
    if type(offset) is not int:raise ValueError('running offset must be integer')
    matches=re.findall(r'(?:Loaded app from partition at offset|RUNNING_PARTITION_OFFSET\s*=)\s*(0x[0-9a-fA-F]+)',text)
    if not matches or {int(s,16) for s in matches}!={offset}:raise ValueError('BLOCKED: no unambiguous actual loaded partition offset; ROM entry address is not enough')
    if len(analysis['partition_candidates'])!=1:raise ValueError('BLOCKED: actual partition table ambiguous/missing')
    app=next((p for p in analysis['partition_candidates'][0]['apps'] if p['offset']==offset),None)
    if app is None or app['image']['image_integrity']!='VALID_LOCAL_BYTES' or analysis['bootloader_at_rom_s3_offset0']['image_integrity']!='VALID_LOCAL_BYTES':raise ValueError('BLOCKED: bootloader/application bytes not verified')
    return {'kind':'FORCAT_REVIEWED_RUNNING_PARTITION_V1','backup_sha256':analysis['full_backup_sha256'],
        'running_app_offset':offset,'table_offset':analysis['partition_candidates'][0]['table_offset'],
        'evidence_log_file':str(Path(e['log_file']).resolve()),'evidence_log_sha256':sha(e['log_file']),
        'observer':e['observer'],'review_scope':'OWNER_OBSERVATION_PLUS_OFFLINE_IMAGE_INTEGRITY',
        'flash_authorized':False,'physical_pass':False,'security_efuse_and_electrical_review':'STILL_REQUIRED'}
def validate_boot_review(backup,review,offset,table_offset):
    data=read_json(review)
    if data.get('kind')!='FORCAT_REVIEWED_RUNNING_PARTITION_V1' or data.get('backup_sha256')!=sha(backup) or type(data.get('running_app_offset')) is not int or data['running_app_offset']!=offset or data.get('table_offset')!=table_offset or not data.get('observer'):
        raise ValueError('BLOCKED: running-partition review does not match backup/bank/table')
    if sha(data['evidence_log_file'])!=data['evidence_log_sha256']:raise ValueError('BLOCKED: running-partition log changed')
    return data
def uart_audit(data):
    if len(data)>16*1024*1024:raise ValueError('existing capture budget16MB')
    frames=[];seen=set();crc_errors=0;invalid_headers=0;duplicates=0;at=0;truncated=False
    while at<len(data):
        begin=data.find(b'\xa5\x5a',at)
        if begin<0:break
        if begin+10>len(data):truncated=True;break
        length=struct.unpack_from('<H',data,begin+8)[0]
        if data[begin+2]!=1 or length>256:invalid_headers+=1;at=begin+1;continue
        end=begin+12+length
        if end>len(data):truncated=True;break
        raw=data[begin:end];crc=0xffff
        for byte in raw[2:-2]:
            crc^=byte<<8
            for _ in range(8):crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
        if crc!=int.from_bytes(raw[-2:],'little'):crc_errors+=1;at=begin+1;continue
        identity=(int.from_bytes(raw[3:7],'little'),raw[7],raw[10:-2])
        duplicate=identity in seen;seen.add(identity);duplicates+=int(duplicate)
        if len(frames)>=4096:raise ValueError('frame audit output bound4096')
        frames.append({'byte_offset':begin,'request_id':identity[0],'command':identity[1],'payload_hex':identity[2].hex(),
            'duplicate':duplicate,'meaning':'ACK_RECEIPT_NOT_FEED_SUCCESS' if identity[1]==6 else 'NACK' if identity[1]==7 else 'PAYLOAD_REQUIRES_EXACT_PROFILE_CONTRACT'})
        at=end
    return {'valid_crc_frames':frames,'crc_errors':crc_errors,'invalid_headers':invalid_headers,'duplicates':duplicates,
        'truncated_tail':truncated,'protocol':'UART_V1_CAPTURE_ONLY' if frames else 'NO_VALID_BINARY_FRAME_ASCII_OR_UNKNOWN',
        'transmitted_commands':0,'physical_pass':False,'feed_success_inferred':False}
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action');sub.required=True
    a=sub.add_parser('record-completed');a.add_argument('--label',choices=('A','B'),required=True);a.add_argument('--file',type=Path,required=True);a.add_argument('--log',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--exit-code',type=int,required=True);a.add_argument('--reader-finished',action='store_true');a.add_argument('--device-id',required=True);a.add_argument('--transport',choices=('ROM','STUB'),default='ROM')
    a=sub.add_parser('plan-b');a.add_argument('--record-a',type=Path,required=True);a.add_argument('--new-file',type=Path,required=True);a.add_argument('--tool-python',required=True);a.add_argument('--port',default='COM8')
    a=sub.add_parser('compare');a.add_argument('--record-a',type=Path,required=True);a.add_argument('--record-b',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--owner-reviewed-rom-continuity',action='store_true')
    for name in ('inspect','compare-probes','boot-gate'):
        a=sub.add_parser(name);a.add_argument('--backup',type=Path,required=True);a.add_argument('--receipt',type=Path,required=True)
        if name=='compare-probes':a.add_argument('--probe-manifest',type=Path,required=True)
        if name=='boot-gate':a.add_argument('--evidence',type=Path,required=True)
    a=sub.add_parser('uart-audit');a.add_argument('existing_capture',type=Path)
    a=p.parse_args()
    if a.action=='record-completed':result=record(a.label,a.file,a.log,a.output,a.exit_code,a.reader_finished,a.device_id,a.transport)
    elif a.action=='plan-b':result=plan_b(a.record_a,a.new_file,a.tool_python,a.port)
    elif a.action=='compare':result=compare_pair(a.record_a,a.record_b,a.output,a.owner_reviewed_rom_continuity)
    elif a.action=='compare-probes':result=compare_probes(a.backup,a.receipt,a.probe_manifest)
    elif a.action=='boot-gate':result=boot_gate(a.backup,a.receipt,a.evidence)
    elif a.action=='uart-audit':result=uart_audit(a.existing_capture.read_bytes())
    else:result=inspect(a.backup,a.receipt)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
