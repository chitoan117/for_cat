"""RCv2 operator CLI. All writes/build/probe/HTTP need explicit apply+confirmation.
preflight/integrity are read-only. No command invokes flash, UART, feeding or
Tailscale configuration. No chained auto-deploy, auto-health or auto-rollback.
"""
import sys
sys.dont_write_bytecode=True
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
from integrity import read,sha,verify
from preflight import inventory
from runtime_config import prepare
from native_build import build
from operations import backup,cutover,rollback,probe
from post_verify import verify_http

CONFIRM={'stage':'STAGE_RC_V2','configure':'PREPARE_PRIVATE_RC_V2','build':'BUILD_RC_V2','backup':'BACKUP_RC_V2',
         'probe':'PROBE_ENGINE_ABI','cutover':'CUTOVER_CAMERA_API_ONLY','rollback':'RESTORE_PREVIOUS_USER_UNITS',
         'verify':'VERIFY_READ_ONLY'}
def apply_allowed(action,apply,confirmation):
    if not apply:return False
    if confirmation!=CONFIRM[action]:raise ValueError('explicit confirmation required: '+CONFIRM[action])
    if os.name!='posix' or platform.system()!='Linux':raise ValueError('operator actions are Linux-only')
    return True
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('integrity','preflight',*CONFIRM))
    p.add_argument('--release',type=Path,required=True);p.add_argument('--production-root',type=Path,default=Path('/home/toan/for_cat'))
    for name in ('output','build','private','backup','home','python'):p.add_argument('--'+name,type=Path)
    p.add_argument('--hostname');p.add_argument('--viewer');p.add_argument('--remote',action='store_true')
    p.add_argument('--ack-telemetry-blocker',action='store_true');p.add_argument('--apply',action='store_true');p.add_argument('--confirm')
    a=p.parse_args();manifest=verify(a.release)
    if a.action=='integrity':result={'integrity':'PASS','files':len(manifest['files']),'manifest_sha256':sha(a.release/'manifest.json')}
    elif a.action=='preflight':result=inventory(a.release,a.production_root)
    elif not apply_allowed(a.action,a.apply,a.confirm):
        result={'mode':'DRY_RUN','action':a.action,'confirmation_required':CONFIRM[a.action],
                'release_manifest_sha256':sha(a.release/'manifest.json'),'production_changed':False,
                'note':'Review README exact required args. No build, backup, service, config or network action executed.'}
    elif a.action=='stage':
        if not a.output:raise ValueError('--output required')
        source=a.release.resolve();target=a.output.resolve();prod=a.production_root.resolve()
        if target.exists() or prod==target or prod in target.parents or source==target or source in target.parents:raise ValueError('NEW disjoint staging release directory required')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,target);verify(target)
        result={'staged':str(target),'production_changed':False}
    elif a.action=='configure':
        if not a.output or not a.hostname or not a.viewer:raise ValueError('--output --hostname --viewer required')
        for root in (a.release.resolve(),a.production_root.resolve()):
            if a.output.resolve()==root or root in a.output.resolve().parents:raise ValueError('private config outside release/production required')
        result=prepare(a.output,a.hostname,a.viewer)
    elif a.action=='build':
        if not a.output:raise ValueError('--output required')
        result=build(a.release,a.output,a.production_root)
    elif a.action=='backup':
        if not a.output:raise ValueError('--output required')
        result=backup(a.release,a.production_root,a.output,a.home or Path.home())
    elif a.action=='probe':
        if not a.build:raise ValueError('--build required')
        result=probe(a.release,a.build,a.production_root)
    elif a.action=='cutover':
        if not all((a.build,a.private,a.backup,a.python)):raise ValueError('--build --private --backup --python required')
        if Path(sys.executable).resolve()!=a.python.resolve():raise ValueError('run control with the selected integration Python')
        result=cutover(a.release,a.build,a.private,a.production_root,a.backup,a.python,a.home or Path.home(),a.ack_telemetry_blocker)
    elif a.action=='rollback':
        if not a.backup:raise ValueError('--backup required')
        result=rollback(a.backup,a.home or Path.home())
    else:
        if not a.private:raise ValueError('--private required')
        result=verify_http(a.private,a.remote)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
