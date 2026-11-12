"""Backup recovery: plans, explicit OWNER-only Windows READS, offline assembly.
No write_flash/erase/actuator/service commands. Old Jetson probes are NEVER opened
for writing. Every read attempt and assembled output is exclusive/new.
Python3.6-compatible for inventory/analysis; actual reader pins Windows+esptool4.8.1.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from image_layout import FLASH_SIZE,sha,partitions,image_header

PLAN_KIND='FORCAT_READ_ONLY_FLASH_BACKUP_PLAN_V1'
RECEIPT_KIND='FORCAT_VERIFIED_FLASH_BACKUP_V1'
def utc():return datetime.now(timezone.utc).isoformat()
def new_json(path,data):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def mac(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}',value):raise ValueError('actual device MAC required, not port name')
    return value.lower()
def inventory(root):
    root=Path(root)
    if not root.is_dir():raise ValueError('existing evidence directory required')
    files=[]
    for path in sorted(root.rglob('*')):
        if path.is_symlink():continue
        if path.is_file():files.append({'name':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
    return {'kind':'EXISTING_PROBES_READ_ONLY_INVENTORY','root':str(root),'files':files,
        'full_backup_verified':False,'physical_pass':False,'old_files_modified':False,
        'note':'File names/sizes alone do not prove addresses, successful reads or full coverage. No old probes auto-merged.'}
def create_plan(folder,device_id,port,tool_python,chunk_size=65536):
    folder=Path(folder)
    if folder.exists():raise ValueError('NEW recovery session required; never overwrite prior probes')
    device_id=mac(device_id)
    if not re.fullmatch(r'COM[1-9][0-9]*',port,re.I):raise ValueError('explicit Windows COM port required')
    if chunk_size not in (4096,16384,65536,262144,1048576,FLASH_SIZE):raise ValueError('supported aligned chunk size required')
    folder.mkdir(parents=True,exist_ok=False)
    data={'kind':PLAN_KIND,'created_utc':utc(),'device_id':device_id,'chip':'esp32s3','flash_size':FLASH_SIZE,
        'port':port,'tool_python':str(Path(tool_python).resolve()),'esptool_version':'4.8.1','baud':115200,
        'transport':'STUB','before':'no_reset','after':'no_reset','chunk_size':chunk_size,
        'chunks':[{'index':i,'offset':at,'size':min(chunk_size,FLASH_SIZE-at)} for i,at in enumerate(range(0,FLASH_SIZE,chunk_size))],
        'required_passes':['a','b'],'application_must_remain_in_rom':True,'physical_pass':False,
        'mode':'PLAN_ONLY_NO_DEVICE_OPEN'}
    new_json(folder/'plan.json',data)
    return data
def load_plan(folder):
    plan=read_json(Path(folder)/'plan.json')
    if plan.get('kind')!=PLAN_KIND or plan.get('flash_size')!=FLASH_SIZE or plan.get('chip')!='esp32s3' or plan.get('esptool_version')!='4.8.1':raise ValueError('wrong backup plan')
    mac(plan['device_id'])
    if not re.fullmatch(r'COM[1-9][0-9]*',plan['port'],re.I):raise ValueError('invalid COM port')
    expected=0
    for i,chunk in enumerate(plan['chunks']):
        if chunk['index']!=i or type(chunk['offset']) is not int or type(chunk['size']) is not int or chunk['offset']!=expected or chunk['size']<=0 or chunk['size']%4096:raise ValueError('invalid/gapped chunk plan')
        expected+=chunk['size']
    if expected!=FLASH_SIZE:raise ValueError('plan coverage not16MB')
    return plan
def read_argv(plan,chunk,destination):
    # Construct, never execute arbitrary argv stored in an edited manifest.
    return [plan['tool_python'],'-B','-m','esptool','--chip','esp32s3','--port',plan['port'],
        '--baud','115200','--before','no_reset','--after','no_reset','read_flash','--flash_size','16MB',
        hex(chunk['offset']),hex(chunk['size']),str(destination)]
def process(argv,timeout=180):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1'))
    return p.returncode,p.stdout
def windows_host():return os.name=='nt'
def take_read(folder,index,pass_name,attempt='1',execute=False,confirm=None,rom_ready=False,runner=process):
    folder=Path(folder).resolve();plan=load_plan(folder)
    if pass_name not in ('a','b') or not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',attempt):raise ValueError('pass a/b and safe attempt label required')
    if type(index) is not int or not 0<=index<len(plan['chunks']):raise ValueError('chunk index')
    chunk=plan['chunks'][index];base=folder/'reads'/('pass_'+pass_name)/('offset_%08x_try_%s'%(chunk['offset'],attempt))
    binary=base.with_suffix('.bin');log=base.with_suffix('.log');receipt=base.with_suffix('.json')
    argv=read_argv(plan,chunk,binary)
    if not execute:return {'mode':'PLAN_ONLY','argv':argv,'device_opened':False,'physical_pass':False}
    if confirm!='OWNER_READ_ONLY_BACKUP' or not rom_ready or not windows_host():raise ValueError('Windows owner read confirmation + ROM/power review required')
    if any(p.exists() for p in (binary,log,receipt)):raise ValueError('attempt exists; preserve even failed/truncated files, use NEW attempt label')
    version_code,version=runner([plan['tool_python'],'-B','-c','import esptool; print(esptool.__version__)'])
    if version_code!=0 or version.decode('utf-8','replace').strip()!='4.8.1':raise ValueError('dedicated Windows esptool4.8.1 environment required')
    base.parent.mkdir(parents=True,exist_ok=True)
    data={'kind':'FORCAT_READ_ATTEMPT_V1','created_utc':utc(),'index':index,'pass':pass_name,'offset':chunk['offset'],
        'size':chunk['size'],'device_id':plan['device_id'],'argv':argv,'returncode':None,'complete':False,
        'ROM_CONTINUITY':'OWNER_DECLARED_NO_APPLICATION_BOOT_BETWEEN_READS','physical_pass':False}
    # Reserve names before talking to the port. The device tool must NOT replace
    # an existing output. Newly reserved .bin is checked by existence above.
    new_json(receipt,data)
    try:
        code,out=runner(argv);data['returncode']=code
    except subprocess.TimeoutExpired as e:
        out=(e.stdout or b'')+b'\nCAPTURE_TIMEOUT';data['error']='TimeoutExpired'
    log.write_bytes(out)
    text=out.decode('utf-8','replace')
    ids={m.lower() for m in re.findall(r'\bMAC:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})',text)}
    data['observed_device_ids']=sorted(ids)
    data['binary_bytes']=binary.stat().st_size if binary.is_file() else 0
    data['log_sha256']=sha(log)
    if binary.is_file():data['binary_sha256']=sha(binary)
    data['complete']=data['returncode']==0 and data['binary_bytes']==chunk['size'] and ids=={plan['device_id']} and 'ESP32-S3' in text
    # A negative/partial read is retained; never converted to an all-FF tail.
    data['binary']=binary.relative_to(folder).as_posix();data['log']=log.relative_to(folder).as_posix()
    receipt.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return data
def child(root,name):
    if not isinstance(name,str) or name.startswith('/') or '\\' in name or ':' in name or any(p in ('','.','..') for p in name.split('/')):raise ValueError('unsafe evidence path')
    p=Path(root)/name
    if not p.is_file() or p.is_symlink() or Path(root).resolve() not in p.resolve().parents:raise ValueError('missing/outside/symlink read evidence')
    return p
def assemble(folder,output,receipt_path,rom_continuity_reviewed=False):
    folder=Path(folder).resolve();plan=load_plan(folder);output=Path(output);receipt_path=Path(receipt_path)
    if output.exists() or receipt_path.exists():raise ValueError('NEW assembled output and receipt required')
    if not rom_continuity_reviewed:raise ValueError('owner must review same-device/ROM continuity before assembly')
    verified={};failed=[]
    for p in sorted((folder/'reads').glob('pass_*/*.json')):
        r=read_json(p)
        if not r.get('complete'):failed.append(str(p));continue
        i=r['index'];which=r['pass']
        if which not in ('a','b') or type(i) is not int or not 0<=i<len(plan['chunks']):raise ValueError('bad read identity')
        c=plan['chunks'][i]
        if r.get('kind')!='FORCAT_READ_ATTEMPT_V1' or r.get('returncode')!=0 or r['device_id']!=plan['device_id'] or r.get('observed_device_ids')!=[plan['device_id']] or (r['offset'],r['size'])!=(c['offset'],c['size']):raise ValueError('device/address/size mismatch')
        binary=child(folder,r['binary']);log=child(folder,r['log'])
        if binary.stat().st_size!=c['size'] or sha(binary)!=r['binary_sha256'] or sha(log)!=r['log_sha256']:raise ValueError('read evidence integrity mismatch')
        key=(i,which)
        if key in verified and verified[key]['binary_sha256']!=r['binary_sha256']:raise ValueError('ambiguous changed data across successful attempts; new snapshot/session review required')
        verified[key]=r
    ranges=[]
    for c in plan['chunks']:
        a=verified.get((c['index'],'a'));b=verified.get((c['index'],'b'))
        if a is None or b is None:raise ValueError('incomplete two-pass coverage at0x%x'%c['offset'])
        if a['binary']==b['binary'] or a['binary_sha256']!=b['binary_sha256']:raise ValueError('independent pass mismatch')
        ranges.append({'offset':c['offset'],'size':c['size'],'sha256':a['binary_sha256'],'pass_a':a['binary'],'pass_b':b['binary']})
    with output.open('xb') as f:
        for r in ranges:f.write(child(folder,r['pass_a']).read_bytes())
    if output.stat().st_size!=FLASH_SIZE:raise ValueError('assembled size mismatch')
    result={'kind':RECEIPT_KIND,'created_utc':utc(),'bytes':FLASH_SIZE,'sha256':sha(output),'device_id':plan['device_id'],
        'coverage_bytes':sum(r['size'] for r in ranges),'contiguous_from_zero':True,'two_independent_passes_match':True,
        'ranges':ranges,'failed_attempts_preserved':failed,'plan_sha256':sha(folder/'plan.json'),
        'rom_continuity':'OWNER_REVIEWED','physical_pass':False,'flash_write_authorized':False,
        'note':'Local consistency receipt, not physical acceptance or boot-bank proof. No padding/erase/refit.'}
    new_json(receipt_path,result);return result
def validate_receipt(backup,receipt_path):
    receipt=read_json(receipt_path)
    if receipt.get('kind')=='FORCAT_OWNER_CONFIRMED_AB_FILES_V1':
        from completed_backup_pair import validate_receipt as completed_receipt
        return completed_receipt(backup,receipt)
    if receipt.get('kind')!=RECEIPT_KIND or receipt.get('bytes')!=FLASH_SIZE or receipt.get('coverage_bytes')!=FLASH_SIZE or receipt.get('contiguous_from_zero') is not True or receipt.get('two_independent_passes_match') is not True or receipt.get('rom_continuity')!='OWNER_REVIEWED':raise ValueError('verified16MB two-pass receipt required')
    mac(receipt['device_id']);cursor=0
    with Path(backup).open('rb') as f:
        for r in receipt.get('ranges',[]):
            if type(r.get('offset')) is not int or type(r.get('size')) is not int or r['offset']!=cursor or r['size']<=0 or cursor+r['size']>FLASH_SIZE:raise ValueError('receipt ranges have gap/overlap')
            if r.get('pass_a')==r.get('pass_b') or not r.get('pass_a') or not r.get('pass_b'):raise ValueError('receipt must identify independent pass files')
            import hashlib
            if hashlib.sha256(f.read(r['size'])).hexdigest()!=r.get('sha256'):raise ValueError('receipt range digest mismatch')
            cursor+=r['size']
    if cursor!=FLASH_SIZE or Path(backup).stat().st_size!=FLASH_SIZE or sha(backup)!=receipt['sha256']:raise ValueError('backup receipt/hash mismatch')
    return receipt
def inspect_backup(backup):
    p=Path(backup)
    if p.stat().st_size!=FLASH_SIZE:raise ValueError('full16MB image required')
    data=p.read_bytes();tables=[]
    for at in range(0,FLASH_SIZE-4096+1,4096):
        if data[at:at+2]!=b'\xaa\x50':continue
        try:items=partitions(data[at:at+4096])
        except (ValueError,UnicodeError):continue
        tables.append({'offset':at,'partitions':items,'apps':[{'offset':r['offset'],'size':r['size'],'image_header':
            image_header(data[r['offset']:r['offset']+24]) if data[r['offset']:r['offset']+1]==b'\xe9' else None} for r in items if r['type']==0]})
    return {'backup_sha256':sha(p),'partition_candidates':tables,'active_boot_bank':'NOT_VERIFIED_REQUIRES_OWNER_BOOT_EVIDENCE',
            'flash_plan_authorized':False,'physical_pass':False}
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action');sub.required=True
    a=sub.add_parser('inventory');a.add_argument('existing_directory',type=Path)
    a=sub.add_parser('plan');a.add_argument('--session',type=Path,required=True);a.add_argument('--device-id',required=True);a.add_argument('--port',required=True);a.add_argument('--tool-python',required=True);a.add_argument('--chunk-size',type=lambda v:int(v,0),default=65536)
    a=sub.add_parser('read');a.add_argument('--session',type=Path,required=True);a.add_argument('--index',type=int,required=True);a.add_argument('--pass',dest='pass_name',choices=('a','b'),required=True);a.add_argument('--attempt',default='1');a.add_argument('--execute',action='store_true');a.add_argument('--confirm');a.add_argument('--rom-ready-ack',action='store_true')
    a=sub.add_parser('assemble');a.add_argument('--session',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--receipt',type=Path,required=True);a.add_argument('--owner-reviewed-rom-continuity',action='store_true')
    a=sub.add_parser('inspect');a.add_argument('full_backup',type=Path)
    a=p.parse_args()
    if a.action=='inventory':result=inventory(a.existing_directory)
    elif a.action=='plan':result=create_plan(a.session,a.device_id,a.port,a.tool_python,a.chunk_size)
    elif a.action=='read':result=take_read(a.session,a.index,a.pass_name,a.attempt,a.execute,a.confirm,a.rom_ready_ack)
    elif a.action=='assemble':result=assemble(a.session,a.output,a.receipt,a.owner_reviewed_rom_continuity)
    else:result=inspect_backup(a.full_backup)
    print(json.dumps(result,indent=2))
    if a.action=='read' and a.execute and not result.get('complete'):raise SystemExit(1)
if __name__=='__main__':main()
