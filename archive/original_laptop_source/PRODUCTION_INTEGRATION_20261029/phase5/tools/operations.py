"""Supervised future writes; called only after control.py confirmation gates.
All service operations use systemctl --user. Never changes bridge unit or env,
legacy binaries/engine, firmware or actuator configuration. No automatic rollback.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
from integrity import absolute,read,sha,verify,verify_backup,write_new
from preflight import service_info,schema_check,ENGINE,ENGINE_SHA,SERVICES,query
from runtime_config import validate

UNITS=SERVICES[:2]
OVERRIDE='90-forcat-rc-v2.conf'
def must(argv,runner=query):
    result=runner(argv)
    if result.get('code')!=0:raise RuntimeError('command failed: '+' '.join(map(str,argv)))
    return result
def paths(home):return {s:Path(home)/'.config/systemd/user'/(s+'.d')/OVERRIDE for s in UNITS}
def render(release,build,private,production,python,template=None):
    values={n:absolute(str(v)).as_posix() for n,v in {'release':release,'build':build,'private':private,'production':production,'python':python}.items()}
    if template is None:template=(Path(release)/'systemd/candidate-override.conf.in').read_text()
    return {s:template.format(**values,role=role) for s,role in zip(UNITS,('ai','api'))}
def backup(release,production,destination,home,runner=query):
    release=Path(release).resolve();production=Path(production).resolve();destination=Path(destination).resolve()
    verify(release)
    if destination.exists() or production in destination.parents or release in destination.parents:raise ValueError('NEW external backup directory required')
    infos={s:service_info(s,runner) for s in SERVICES}
    if any(v['query'].get('code')!=0 or not v['fields'].get('FragmentPath') for v in infos.values()):raise ValueError('all live user units must be inventoried before backup')
    destination.mkdir(parents=True,exist_ok=False,mode=0o700)
    dbpath=production/'jetson/data/events.db'
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True,timeout=1) as src, sqlite3.connect(destination/'events.sqlite3') as dst:
        src.backup(dst);integrity=dst.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity!='ok':raise ValueError('consistent DB backup failed')
    files={'events.sqlite3':sha(destination/'events.sqlite3')};originals={};overrides={}
    def capture(source):
        source=Path(source)
        if source.is_symlink() or not source.is_file():raise ValueError('unit source must be regular readable file: '+str(source))
        name='unit_'+str(len(files))+'.backup';shutil.copyfile(source,destination/name);os.chmod(destination/name,0o600)
        files[name]=sha(destination/name);originals[str(source)]={'backup_file':name,'sha256':files[name]}
        return name
    for s,info in infos.items():
        unit_files=[info['fields']['FragmentPath']]+shlex.split(info['fields'].get('DropInPaths',''))
        for path in unit_files:
            if path not in originals:capture(path)
    for s,path in paths(home).items():overrides[s]={'path':str(path),'backup_file':capture(path) if path.exists() else None}
    detector=production/'jetson/ai/cat_dog_trt'
    supervisor=production/'scripts/run_existing_ai.sh'
    receipt={'kind':'FORCAT_BACKUP_V2','release_manifest_sha256':sha(release/'manifest.json'),
        'production_root':str(production),'home':str(Path(home).resolve()),'files':files,'originals':originals,
        'overrides':overrides,'services':infos,'database_integrity':integrity,'database_snapshot':'events.sqlite3',
        'protected_hashes':{str(p):sha(p) for p in (detector,supervisor,production/'models/tensorrt/yolov8n_320_fp16.engine') if p.is_file()}}
    write_new(destination/'backup.json',receipt);os.chmod(destination/'backup.json',0o600)
    (destination/'backup.sha256').write_text(sha(destination/'backup.json')+'\n')
    os.chmod(destination/'events.sqlite3',0o600)
    verify_backup(destination)
    return {'backup':str(destination),'integrity':'ok','production_changed':False}
def stopped(runner=query):
    for s in UNITS:
        result=runner(['systemctl','--user','is-active',s])
        if result.get('stdout','').strip() not in ('inactive','failed') or result.get('code') not in (3,):raise ValueError('service not confirmed stopped: '+s)
def free_camera(runner=query):
    result=runner(['fuser','/dev/video0'])
    if result.get('code')!=1 or result.get('stderr','').strip():raise ValueError('camera owner remains or ownership unavailable')
def no_writer(db):
    import fcntl
    lock=Path(str(db)+'-ai.lock')
    if lock.exists():
        with lock.open('rb') as f:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
def binary_receipt(release,build):
    data=read(Path(build)/'build.json')
    if data.get('arm64_build')!='PASS' or data['release_manifest_sha256']!=sha(Path(release)/'manifest.json'):raise ValueError('matching ARM64 build required')
    for name,digest in data['binaries'].items():
        if name not in ('roi_ai_source','esp32_bridge','ai_state_tap','engine_probe') or sha(Path(build)/name)!=digest:raise ValueError('build artifact mismatch')
    if set(data['binaries'])!={'roi_ai_source','esp32_bridge','ai_state_tap','engine_probe'}:raise ValueError('missing native artifacts')
    return data
def probe(release,build,production,runner=query):
    binary_receipt(release,build);stopped(runner);free_camera(runner)
    engine=Path(production)/'models/tensorrt/yolov8n_320_fp16.engine'
    if str(engine)!=ENGINE or sha(engine)!=ENGINE_SHA:raise ValueError('reviewed engine path/hash mismatch')
    result=must([str(Path(build)/'engine_probe'),str(engine)],runner)
    if json.loads(result['stdout']).get('engine_contract')!='PASS':raise ValueError('engine probe did not pass')
    return {'engine_contract':'PASS','engine_sha256':sha(engine),'probe_binary_sha256':sha(Path(build)/'engine_probe')}
def atomic_text(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.rc-v2-new')
    with temporary.open('x') as f:f.write(text)
    os.replace(temporary,path)
def cutover(release,build,private,production,backup_dir,python,home,ack_telemetry=False,runner=query,writer_check=no_writer,probe_fn=probe):
    release=Path(release).resolve();production=Path(production).resolve();build=Path(build).resolve();home=Path(home).resolve()
    verify(release);validate(private);binary_receipt(release,build)
    prior=verify_backup(backup_dir)
    if prior['release_manifest_sha256']!=sha(release/'manifest.json') or prior['production_root']!=str(production) or prior['home']!=str(home):raise ValueError('backup does not match deployment')
    if not ack_telemetry:raise ValueError('explicit acknowledgement required: HX711_REFERENCE telemetry remains NOT_VERIFIED; camera/API only')
    for s in UNITS:
        fields=prior['services'][s]['fields']
        if any(k not in fields or fields[k].strip() for k in ('ExecStartPre','ExecStartPost','ExecStop','ExecStopPost')):
            raise ValueError('unknown/nonempty service lifecycle hooks require owner review before cutover')
    for path,meta in prior['originals'].items():
        if sha(path)!=meta['sha256']:raise ValueError('unit changed since backup; stop for owner review')
    for data in prior['overrides'].values():
        if data['backup_file'] is None and Path(data['path']).exists():raise ValueError('new override appeared after backup')
    schema=schema_check(production/'jetson/data/events.db',read(release/'schema/contract.json'))
    if not schema['compatible']:raise ValueError('schema conflict; do not auto-migrate')
    texts=render(release,build,private,production,python)
    journal=Path(backup_dir)/'cutover.json'
    write_new(journal,{'state':'STARTED_NO_AUTO_ROLLBACK','release':str(release),'planned_overrides':texts,
                       'database_restore_on_rollback':False,'known_esp32_blocker':True})
    for s in reversed(UNITS):must(['systemctl','--user','stop',s],runner)
    stopped(runner);free_camera(runner);writer_check(production/'jetson/data/events.db')
    probe_result=probe_fn(release,build,production,runner)
    write_new(Path(backup_dir)/'engine_probe.json',probe_result)
    # Syntax-check concrete drop-ins offline on the TARGET before installing.
    for s,text in texts.items():
        concrete=Path(backup_dir)/(s+'.candidate.service')
        concrete.write_text('[Unit]\nDescription=FORCAT candidate syntax validation\n'+text+'\n')
        must(['systemd-analyze','--user','verify',str(concrete)],runner)
    for s,path in paths(home).items():atomic_text(path,texts[s])
    must(['systemctl','--user','daemon-reload'],runner)
    for s,role in zip(UNITS,('ai','api')):
        effective=must(['systemctl','--user','show',s,'--property=ExecStart'],runner)['stdout']
        if str(release/'tools/managed_runtime.py') not in effective or ' '+role+' ' not in effective:raise ValueError('effective ExecStart mismatch; services remain stopped; explicit rollback required')
    must(['systemctl','--user','start',UNITS[1]],runner)
    must(['systemctl','--user','start',UNITS[0]],runner)
    write_new(Path(backup_dir)/'cutover_applied.json',{'state':'STARTED_AWAIT_HEALTH_CHECK','installed_sha256':{s:sha(p) for s,p in paths(home).items()}})
    return {'state':'STARTED_AWAIT_HEALTH_CHECK','auto_rollback':False,'ESP32_TELEMETRY_PASS':'NOT_VERIFIED','actuators':'LOCKED'}
def rollback(backup_dir,home,runner=query,writer_check=no_writer):
    data=verify_backup(backup_dir);home=Path(home).resolve()
    if data['home']!=str(home):raise ValueError('backup home mismatch')
    own_paths=paths(home)
    if any(data['overrides'][s]['path']!=str(p) for s,p in own_paths.items()):raise ValueError('unexpected restore destination')
    for path,meta in data['originals'].items():
        if path not in {str(p) for p in own_paths.values()} and sha(path)!=meta['sha256']:
            raise ValueError('base unit changed by owner; review before rollback')
    # Never overwrite owner edits made after a partially/completely applied cutover.
    applied=Path(backup_dir)/'cutover_applied.json'
    journal=read(Path(backup_dir)/'cutover.json')
    for s,p in own_paths.items():
        if p.exists():
            old=data['overrides'][s]['backup_file']
            expected=[journal['planned_overrides'][s]]
            if old:expected.append((Path(backup_dir)/old).read_text())
            if p.read_text() not in expected:raise ValueError('override modified by owner; manual review required')
    for s in reversed(UNITS):must(['systemctl','--user','stop',s],runner)
    stopped(runner);free_camera(runner);writer_check(Path(data['production_root'])/'jetson/data/events.db')
    for s,p in own_paths.items():
        old=data['overrides'][s]['backup_file']
        if old:atomic_text(p,(Path(backup_dir)/old).read_text())
        elif p.exists():p.unlink() # only our exact, verified drop-in, never arbitrary user files
    must(['systemctl','--user','daemon-reload'],runner)
    for s in reversed(UNITS):
        if data['services'][s]['fields']['ActiveState']=='active':must(['systemctl','--user','start',s],runner)
    return {'state':'RESTORED_PREVIOUS_USER_UNIT_CONFIGURATION','database_restored':False,'engine_changed':False,'manual_health_check_required':True}
