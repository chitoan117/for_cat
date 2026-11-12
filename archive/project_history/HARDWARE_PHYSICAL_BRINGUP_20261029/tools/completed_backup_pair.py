"""Owner-confirmed completed A/B file acceptance; NO device/process operations.
Accepts new owner completion/hash evidence, does not re-request historic exitcodes.
"""
from pathlib import Path
import re
from image_layout import FLASH_SIZE,sha

KIND='FORCAT_OWNER_CONFIRMED_AB_FILES_V1'
def validate_pair(a,b,expected):
    expected=expected.lower()
    if not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('expected SHA256 required')
    a=Path(a).resolve();b=Path(b).resolve()
    if a==b or a.samefile(b):raise ValueError('independent A/B files required')
    result=[]
    for p in (a,b):
        if p.is_symlink() or not p.is_file():raise ValueError('regular completed backup required')
        before=p.stat()
        if before.st_size!=FLASH_SIZE:raise ValueError('exact16777216bytes required')
        digest=sha(p);after=p.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('backup changed during readonly check')
        if digest!=expected:raise ValueError('A/B or owner SHA mismatch')
        result.append({'file':str(p),'bytes':after.st_size,'sha256':digest})
    return {'kind':KIND,'owner_completion_markers':['BACKUP_A_B_SHA256_MATCH=YES','BACKUP_B_READ_COMPLETE'],
        'expected_sha256':expected,'bytes':FLASH_SIZE,'sha256':expected,'files':result,'backup_AB_file_integrity':'PASS',
        'read_success_authority':'OWNER_CONFIRMED_BOTH_COMPLETED_PLUS_DIRECT_FILE_HASH_CHECK',
        'device_identity_binding':'OWNER_REPORTED_ESP32S3_REV0.2_CH343_NO_NEW_DEVICE_READ',
        'physical_pass':False,'flash_authorized':False,'third_read_required':False,'old_exitcode_requested':False}
def validate_receipt(backup,receipt):
    if receipt.get('kind')!=KIND or receipt.get('backup_AB_file_integrity')!='PASS' or receipt.get('bytes')!=FLASH_SIZE or len(receipt.get('files',[]))!=2:raise ValueError('bad completed A/B receipt')
    pair=validate_pair(receipt['files'][0]['file'],receipt['files'][1]['file'],receipt['expected_sha256'])
    if Path(backup).resolve() not in [Path(r['file']) for r in pair['files']] or receipt['sha256']!=pair['sha256']:raise ValueError('backup does not match accepted pair')
    return receipt
