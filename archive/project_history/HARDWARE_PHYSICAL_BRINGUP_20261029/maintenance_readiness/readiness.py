"""Python3.6+, PLAN default; explicit collect reads metadata/files only.
No serial/esptool import, no service mutations, no device reads.
"""
from __future__ import print_function
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

HERE=Path(__file__).resolve().parent
KIT=HERE.parent
UNIT='for-cat-esp32-bridge.service'
EXE='/home/toan/for_cat/.native-build/esp32/esp32_bridge'
PORT='/dev/ttyACM0'
BYID='/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00'
AI='for-cat-ai.service'
API='for-cat-api.service'
NATIVE='web_hardware/native_arm64_gcc75_r1_20261029_171958/result.json'
SENSOR_SHA='a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56'
ROLLBACK_SHA='820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826'
QUALIFIED_SHA='2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c'
FIELDS=('LoadState','ActiveState','SubState','MainPID','ExecStart','FragmentPath',
        'DropInPaths','ControlGroup','Restart','UnitFileState','NeedDaemonReload')

def utc():return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def regular(path):return Path(path).is_file() and not Path(path).is_symlink()
def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def new_dir(path):
    path=Path(path).absolute()
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise ValueError('NEW output directory with existing parent required')
    path.mkdir(mode=0o700)
    return path
def unit_name(value):
    if not re.match(r'^[A-Za-z0-9_.@-]+\.service$',value):raise ValueError('invalid unit name')
    return value
def command(argv):
    try:
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        return {'argv':argv,'code':p.returncode,'stdout':p.stdout.decode('utf-8','replace'),
                'stderr':p.stderr.decode('utf-8','replace')}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'argv':argv,'code':125,'stdout':'','stderr':str(e)}
def show(unit,runner=command):
    argv=['systemctl','--user','show',unit]
    for key in FIELDS:argv+=['-p',key]
    raw=runner(argv)
    return dict(line.split('=',1) for line in raw['stdout'].splitlines() if '=' in line),raw
def holders(runner=command):
    r=runner(['fuser',PORT]);text=r['stdout'].strip()
    if r['code']==1 and not text and not r['stderr'].strip():return [],r
    if r['code']==0 and text and all(x.isdigit() for x in text.split()):
        # fuser normally writes only the device prefix to stderr.
        if r['stderr'].strip() not in ('',PORT+':'):raise ValueError('ambiguous fuser diagnostic')
        return sorted(set(int(x) for x in text.split())),r
    raise ValueError('fuser unavailable/error/visibility unknown: '+r['stderr'])
def host_identity():
    p=Path(BYID)
    target=str(p.resolve(strict=True))
    if target!=PORT or not stat.S_ISCHR(p.stat().st_mode):raise ValueError('stable USB path does not resolve to expected tty character device')
    return target
def assess(snapshot):
    problems=[];b=snapshot['bridge']
    if b.get('LoadState')!='loaded' or b.get('ActiveState')!='active' or b.get('SubState')!='running':problems.append('BRIDGE_NOT_ACTIVE_RUNNING')
    if b.get('NeedDaemonReload')!='no':problems.append('UNIT_CONFIGURATION_NOT_CURRENT')
    try:pid=int(b.get('MainPID','0'))
    except ValueError:pid=0
    if pid<=0 or snapshot.get('holders')!=[pid]:problems.append('SERIAL_OWNER_NOT_SOLE_CURRENT_MAINPID')
    if snapshot.get('executable')!=EXE:problems.append('UNEXPECTED_EXECUTABLE')
    if snapshot.get('device')!=PORT:problems.append('USB_IDENTITY_UNVERIFIED')
    usb=snapshot.get('usb',{})
    if usb.get('ID_VENDOR_ID','').lower()!='1a86' or usb.get('ID_SERIAL_SHORT')!='5C85066678':problems.append('USB_PROPERTIES_MISMATCH')
    for key in ('ai','api'):
        if snapshot[key].get('LoadState')!='loaded' or snapshot[key].get('ActiveState')!='active':problems.append(key.upper()+'_NOT_ACTIVE')
    if snapshot.get('inspection_errors'):problems+=snapshot['inspection_errors']
    return problems

def snapshot(out,ai=AI,api=API,runner=command,identity=host_identity):
    data={'created_utc':utc(),'bridge_unit':UNIT,'ai_unit':unit_name(ai),'api_unit':unit_name(api),
          'historical_owner_PID':3989,'inspection_errors':[], 'device':None, 'holders':None,
          'executable':None,'usb':{},'agent_or_user_scope':'READONLY_METADATA_NO_SERIAL_OPEN'}
    for key,unit in (('bridge',UNIT),('ai',ai),('api',api)):
        properties,raw=show(unit,runner);data[key]=properties;write_new(out/(key+'_show.json'),raw)
        if raw['code']!=0:data['inspection_errors'].append(key.upper()+'_SHOW_FAILED')
    for name,argv in (
        ('bridge_unit',['systemctl','--user','cat',UNIT]),
        ('journal',['journalctl','--user','-u',UNIT,'-b','--no-pager','-o','short-iso','-n','400']),
        ('usb',['udevadm','info','--query=property','--name='+PORT])):
        raw=runner(argv);write_new(out/(name+'_output.json'),raw)
        if name=='usb' and raw['code']==0:data['usb']=dict(x.split('=',1) for x in raw['stdout'].splitlines() if '=' in x)
        if name=='bridge_unit' and raw['code']!=0:data['inspection_errors'].append('UNIT_FILE_BACKUP_FAILED')
    try:data['device']=identity()
    except (OSError,ValueError) as e:data['inspection_errors'].append(str(e))
    try:data['holders'],raw=holders(runner);write_new(out/'serial_holders.json',raw)
    except ValueError as e:data['inspection_errors'].append(str(e))
    try:
        pid=int(data['bridge'].get('MainPID','0'))
        if pid>0:
            p=Path('/proc')/str(pid)/'exe'
            data['executable']=os.readlink(str(p));data['running_executable_sha256']=sha(p)
    except (ValueError,OSError) as e:data['inspection_errors'].append('EXECUTABLE_INSPECTION_FAILED: '+str(e))
    # Preserve readable unit fragments/drop-ins, not merely their names.
    data['unit_files']=[]
    paths=[data['bridge'].get('FragmentPath','')]+data['bridge'].get('DropInPaths','').split()
    for n,name in enumerate(x for x in paths if x):
        p=Path(name)
        try:
            if not p.is_file():raise ValueError('not a regular unit file')
            target=out/('original_unit_%02d.txt'%n)
            with target.open('xb') as f:f.write(p.read_bytes())
            data['unit_files'].append({'path':name,'copy':target.name,'sha256':sha(target)})
        except (OSError,ValueError) as e:data['inspection_errors'].append('UNIT_COPY_FAILED: '+str(e))
    if not data['unit_files']:data['inspection_errors'].append('NO_ORIGINAL_UNIT_FILES_CAPTURED')
    data['preflight_issues']=assess(data)
    data['metadata_preflight']='VERIFIED' if not data['preflight_issues'] else 'NO_GO'
    data['APP_FLASH']='NO_GO'
    write_new(out/'snapshot.json',data)
    return data

def attach_existing(out):
    records={}
    for label,rel in (('native_pass',NATIVE),('rollback','web_hardware/rollback_original_app_00010000.bin'),
                      ('sensor','artifacts/diag_four_ultrasonic/firmware.bin')):
        p=KIT/rel
        if not regular(p):records[label]={'state':'NOT_VERIFIED_LOCAL_ATTACHMENT_MISSING','path':str(p)};continue
        raw=p.read_bytes();meta={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if label=='native_pass':
            v=json.loads(raw.decode('utf-8'));meta['existing_result']=v
            ok=(v.get('ARM64_NATIVE_TEST_PASS') is True and v.get('whole_posix_bridge_compile')=='PASS'
                and v.get('food_roi_checks')==115 and len(v.get('replay_cases',[]))==26 and 'checks=17' in v.get('session_stdout',''))
        else:ok=meta['sha256']==(SENSOR_SHA if label=='sensor' else ROLLBACK_SHA)
        meta['state']='VERIFIED_EXISTING_FILE' if ok else 'NO_GO_ATTACHMENT_MISMATCH';records[label]=meta
    write_new(out/'existing_evidence.json',records)
    return records

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect',choices=('READ_ONLY_METADATA',))
    p.add_argument('--output',type=Path)
    p.add_argument('--ai-unit',default=AI);p.add_argument('--api-unit',default=API)
    a=p.parse_args()
    if not a.collect:
        print(json.dumps({'mode':'PLAN_ONLY','bridge':UNIT,'by_id':BYID,
            'next':'--collect READ_ONLY_METADATA --output NEW_DIRECTORY',
            'service_mutations':False,'serial_opened':False,'APP_FLASH':'NO_GO'},indent=2));return
    if sys.platform!='linux':raise ValueError('metadata collection is USER-run Linux only')
    if not a.output:raise ValueError('--output NEW_DIRECTORY required')
    out=new_dir(a.output)
    data=snapshot(out,a.ai_unit,a.api_unit);attach_existing(out)
    print(json.dumps({'output':str(out),'metadata_preflight':data['metadata_preflight'],
        'issues':data['preflight_issues'],'service_mutations':False,'serial_opened':False,'APP_FLASH':'NO_GO'},indent=2))
    if data['preflight_issues']:raise SystemExit(2)

if __name__=='__main__':main()
