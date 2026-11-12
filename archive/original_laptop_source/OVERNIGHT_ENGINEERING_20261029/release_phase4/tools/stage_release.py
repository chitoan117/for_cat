"""Owner-only staging/backup/selection/rollback. Defaults are planning only.

Never writes the production root or invokes a service command. 'current' is a
staging selector ONLY, not a live service switch. A future owner cutover must
explicitly arrange service paths; that live operation is outside this script.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
from datetime import datetime,timezone
from release_bundle import verify

def stage(bundle, staging, production, execute=False):
    bundle=Path(bundle).resolve();staging=Path(staging).resolve();production=Path(production).resolve()
    if staging==production or production in staging.parents or staging in production.parents:
        raise ValueError('staging must be disjoint from production')
    verify(bundle)
    target=staging/'releases'/bundle.name
    if target.exists():raise ValueError('release exists; do not overwrite')
    if execute:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,target)
        verify(target)
    return {'plan_only':not execute,'target':str(target),'production_changed':False}
def select(staging, release, execute=False):
    staging=Path(staging).resolve();release=Path(release).resolve()
    if release.parent!=staging/'releases':raise ValueError('release outside staging/releases')
    verify(release)
    current=staging/'current'
    if current.exists() and not current.is_symlink():raise ValueError('current must be a staging symlink')
    previous=os.readlink(current) if current.is_symlink() else None
    result={'plan_only':not execute,'previous':previous,'selected':str(release),'production_changed':False}
    if execute:
        # Record previous selection before the atomic pointer update; no runtime
        # process/service is started or restarted by selecting a staged release.
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=staging/('selection_backup_'+stamp+'.json')
        with backup.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
        temporary=staging/('current_'+stamp)
        temporary.symlink_to(release,target_is_directory=True);os.replace(temporary,current)
        result['backup']=str(backup)
    return result
def rollback(staging, backup, execute=False):
    staging=Path(staging).resolve();backup=Path(backup).resolve()
    if backup.parent!=staging or not backup.name.startswith('selection_backup_'):raise ValueError('wrong staging backup')
    data=json.loads(backup.read_text(encoding='utf-8'))
    if not data.get('previous'):raise ValueError('no previous release; first selection requires owner removal of staging pointer')
    previous=Path(data['previous'])
    if not previous.is_absolute():previous=staging/previous
    return select(staging,previous,execute)
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('stage');a.add_argument('--bundle',required=True);a.add_argument('--production-root',required=True)
    a=sub.add_parser('select');a.add_argument('--release',required=True)
    a=sub.add_parser('rollback');a.add_argument('--backup',required=True)
    for a in sub.choices.values():a.add_argument('--staging-root',required=True);a.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.command=='stage':result=stage(args.bundle,args.staging_root,args.production_root,args.execute)
    elif args.command=='select':result=select(args.staging_root,args.release,args.execute)
    else:result=rollback(args.staging_root,args.backup,args.execute)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
