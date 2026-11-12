"""RCv2 qualification: all target actions are faked or confined to tmp_path."""
import ast
import configparser
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import types
import pytest

HERE=Path(__file__).resolve().parent;SESSION=HERE.parent;ROOT=SESSION.parent
RELEASE=SESSION/'release_candidate_v2'
sys.path.insert(0,str(HERE/'tools'));sys.path.insert(0,str(HERE))
import integrity as it
import operations as op
import runtime_config as cfg
import preflight as pf
import native_build as nb
import managed_runtime as runtime
import post_verify as pv
import control
import build_release as package

def test_exact_current_source_manifest_phase4_builds_and_all_groups():
    manifest=it.verify(RELEASE);selected=package.collect()
    assert {m['group'] for m in manifest['files'].values()}==set('ABCDEFGHIJ')
    for name,source in selected.items():assert it.sha(RELEASE/name)==it.sha(source),name
    for name,meta in manifest['files'].items():
        assert meta['overwrites_production'] is False and meta['destination']=='${RELEASE_DIR}/'+name
        assert meta['source_path'] and meta['role'] and meta['dependencies']
        assert not name.endswith(('.engine','.sqlite3','.token','.env'))
    assert 'payload/jetson/app/ai_frame_contract.py' in manifest['files']
    assert 'payload/jetson/device/state_wire.h' in manifest['files']
    assert 'release_camera' not in json.dumps([m['source_path'] for m in manifest['files'].values()])
    phase4=it.read(SESSION/'phase4/result.json')
    for mode in ('real','mock'):assert it.sha(RELEASE/'web'/mode/'main.dart.js')==phase4['web_builds'][mode]['main_dart_js_sha256']

@pytest.fixture
def tiny(tmp_path):
    p=tmp_path/'bundle';p.mkdir();(p/'a.py').write_text('x=1\n')
    m={'kind':it.KIND,'files':{'a.py':{'sha256':it.sha(p/'a.py'),'bytes':(p/'a.py').stat().st_size}}}
    it.write_new(p/'manifest.json',m);(p/'manifest.sha256').write_text(it.sha(p/'manifest.json'))
    (p/'SHA256SUMS').write_text(m['files']['a.py']['sha256']+'  a.py\n')
    return p
@pytest.mark.parametrize('name',['../x','/etc/passwd','C:/x','a\\b','a//b','./a'])
def test_manifest_path_escape_rejected(tiny,name):
    m=it.read(tiny/'manifest.json');m['files']={name:next(iter(m['files'].values()))}
    (tiny/'manifest.json').write_text(json.dumps(m));(tiny/'manifest.sha256').write_text(it.sha(tiny/'manifest.json'))
    with pytest.raises(ValueError):it.verify(tiny)
def test_modified_file_and_extra_file_rejected(tiny):
    (tiny/'a.py').write_text('bad!')
    with pytest.raises(ValueError):it.verify(tiny)
    (tiny/'a.py').write_text('x=1\n');(tiny/'extra.token').write_text('private')
    with pytest.raises(ValueError):it.verify(tiny)
@pytest.mark.parametrize('action',list(control.CONFIRM))
def test_default_cli_is_dry_run_no_devices_or_runtime(action):
    p=subprocess.run([sys.executable,'-B',str(RELEASE/'tools/control.py'),action,'--release',str(RELEASE)],capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stderr
    data=json.loads(p.stdout);assert data['mode']=='DRY_RUN' and data['production_changed'] is False
def test_apply_confirmation_and_host_gate():
    assert not control.apply_allowed('cutover',False,None)
    with pytest.raises(ValueError,match='confirmation'):control.apply_allowed('cutover',True,'YES')
    if os.name=='nt':
        with pytest.raises(ValueError,match='Linux'):control.apply_allowed('cutover',True,control.CONFIRM['cutover'])
def test_tools_python_syntax_and_concrete_user_unit_templates():
    for p in (RELEASE/'tools').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),str(p))
    rendered=op.render('/home/toan/release','/home/toan/build','/home/toan/private','/home/toan/for_cat','/home/toan/venv/bin/python',
        (RELEASE/'systemd/candidate-override.conf.in').read_text())
    for s,text in rendered.items():
        c=configparser.ConfigParser(strict=False,interpolation=None);c.optionxform=str;c.read_string(text)
        assert c['Service']['KillMode']=='control-group' and c['Service']['Type']=='simple'
        assert 'managed_runtime.py' in text and '--production-root /home/toan/for_cat' in text
        assert 'run_existing_ai.sh' not in text and 'SERIAL' not in text
    with pytest.raises(ValueError):op.render('/tmp/x%h','/b','/p','/prod','/py')
def test_native_build_commands_are_cxx14_and_never_production_output():
    commands=nb.commands('/release','/staging/build',lambda mode,mods:['--FAKE-'+mode])
    assert set(commands)=={'roi_ai_source','esp32_bridge','ai_state_tap','engine_probe'}
    for name,args in commands.items():
        assert '-std=c++14' in args and args[args.index('-o')+1]=='/staging/build/'+name
    assert '/release/payload/jetson/device/roi_ai_source.cpp' in commands['roi_ai_source']
def test_cuda_paths_follow_selected_target_toolkit_not_assumed_symlink():
    argv=nb.commands('/release','/staging/build',lambda *a:[],cuda_home='/opt/cuda-10.2')['roi_ai_source']
    assert '-I/opt/cuda-10.2/include' in argv and '-L/opt/cuda-10.2/lib64' in argv
    assert not any(x.startswith(('-I/usr/local/cuda/','-L/usr/local/cuda/')) for x in argv)
def test_missing_dependency_preflight_is_readonly_and_not_build_pass(monkeypatch,tmp_path):
    calls=[]
    def fake(argv):calls.append(argv);return {'code':127,'stdout':'','argv':argv}
    data=pf.inventory(RELEASE,tmp_path/'no_production',fake)
    assert not data['build_preconditions'] and data['ARM64_TENSORRT_BUILD_PASS']=='NOT_VERIFIED'
    assert data['camera_opened'] is False and data['production_changed'] is False
    assert all(a[:3]==['systemctl','--user','show'] for a in calls if a[0]=='systemctl')
    assert all(a[0] in ('g++','pkg-config','ldconfig','fuser','v4l2-ctl','id','systemctl') for a in calls)
def test_schema_columns_and_extra_required_columns_fail_closed(tmp_path):
    p=tmp_path/'local.db';contract={'tables':{'ai_latest':{'columns':[{'name':'id','type':'INTEGER','pk':1},{'name':'body','type':'TEXT','pk':0}]}}}
    with sqlite3.connect(p) as db:db.execute('CREATE TABLE ai_latest(id INTEGER PRIMARY KEY,body TEXT, unexpected TEXT NOT NULL)')
    data=pf.schema_check(p,contract)
    assert not data['compatible'] and data['conflicts']==['ai_latest.unexpected EXTRA_REQUIRED_COLUMN']

@pytest.fixture
def rig(tmp_path,monkeypatch):
    production=tmp_path/'production';(production/'jetson/data').mkdir(parents=True)
    dbpath=production/'jetson/data/events.db'
    contract=it.read(RELEASE/'schema/contract.json')
    with sqlite3.connect(dbpath) as db:
        for table in contract['tables'].values():db.execute(table['ddl'])
        db.execute('INSERT INTO ai_latest VALUES(1,?)',('{"SYNTHETIC_TEST_ONLY":true}',))
    home=tmp_path/'home';fragments=tmp_path/'fragments';fragments.mkdir()
    states={s:'active' for s in pf.SERVICES};calls=[]
    for s in pf.SERVICES:(fragments/s).write_text('[Service]\nExecStart=/original/'+s+'\n')
    old=op.paths(home)[pf.SERVICES[0]];old.parent.mkdir(parents=True);old.write_text('OWNER_PREVIOUS_OVERRIDE\n')
    texts={s:'CANDIDATE '+str(RELEASE/'tools/managed_runtime.py')+' '+role+' --fake\n' for s,role in zip(op.UNITS,('ai','api'))}
    monkeypatch.setattr(op,'render',lambda *a:texts)
    camera={'code':1}
    def runner(argv):
        calls.append([str(x) for x in argv]);out='';code=0
        if argv[0]=='systemctl':
            action=argv[2]
            if action=='show':
                s=argv[3]
                if argv[-1]=='--property=ExecStart':out=texts[s]
                else:out='\n'.join(['ActiveState='+states[s],'SubState=running','MainPID=0','FragmentPath='+str(fragments/s),'DropInPaths=',
                     'ExecStartPre=','ExecStartPost=','ExecStop=','ExecStopPost=','Type=simple'])
            elif action=='stop':states[argv[3]]='inactive'
            elif action=='start':states[argv[3]]='active'
            elif action=='is-active':out=states[argv[3]];code=0 if out=='active' else 3
        elif argv[0]=='fuser':code=camera['code']
        return {'code':code,'stdout':out,'argv':argv}
    private=tmp_path/'private';cfg.prepare(private,'forcat.tailtest.ts.net','viewer@test')
    build=tmp_path/'build';build.mkdir()
    bins={}
    for n in ('roi_ai_source','esp32_bridge','ai_state_tap','engine_probe'):(build/n).write_text('FAKE_TEST_ONLY_NOT_ARM64');bins[n]=it.sha(build/n)
    it.write_new(build/'build.json',{'arm64_build':'PASS','release_manifest_sha256':it.sha(RELEASE/'manifest.json'),'binaries':bins,'synthetic_fixture':True})
    backup=tmp_path/'backup';op.backup(RELEASE,production,backup,home,runner)
    def probe(*args):calls.append(['FAKE_ENGINE_PROBE_NOT_PHYSICAL']);return {'engine_contract':'PASS','synthetic_fixture':True}
    def writer(_):calls.append(['FAKE_WRITER_LOCK_FREE'])
    return types.SimpleNamespace(prod=production,home=home,build=build,private=private,backup=backup,runner=runner,calls=calls,
        camera=camera,probe=probe,writer=writer,old=old,texts=texts,states=states,db=dbpath)
def apply_rig(r):return op.cutover(RELEASE,r.build,r.private,r.prod,r.backup,Path('/integration/python'),r.home,True,r.runner,r.writer,r.probe)
def test_backup_consistent_and_cutover_then_explicit_rollback_order(rig):
    r=rig;before=r.db.read_bytes();assert it.verify_backup(r.backup)['database_integrity']=='ok'
    result=apply_rig(r);assert result['state']=='STARTED_AWAIT_HEALTH_CHECK' and not result['auto_rollback']
    stops=[a for a in r.calls if a[:3]==['systemctl','--user','stop']]
    assert [a[3] for a in stops]==['for-cat-api.service','for-cat-ai.service']
    index=r.calls.index(['FAKE_ENGINE_PROBE_NOT_PHYSICAL'])
    assert all(r.calls.index(a)<index for a in stops)
    starts=[a[3] for a in r.calls if a[:3]==['systemctl','--user','start']]
    assert starts==['for-cat-api.service','for-cat-ai.service']
    restored=op.rollback(r.backup,r.home,r.runner,r.writer)
    assert not restored['database_restored'] and r.old.read_text()=='OWNER_PREVIOUS_OVERRIDE\n'
    assert not op.paths(r.home)[pf.SERVICES[1]].exists() and r.db.read_bytes()==before
    assert not any(a[:3]==['systemctl','--user','stop'] and a[3]=='for-cat-esp32-bridge.service' for a in r.calls)
def test_missing_telemetry_ack_blocks_before_service_stop(rig):
    r=rig
    with pytest.raises(ValueError,match='acknowledgement'):op.cutover(RELEASE,r.build,r.private,r.prod,r.backup,Path('/python'),r.home,False,r.runner,r.writer,r.probe)
    assert not any(a[:3]==['systemctl','--user','stop'] for a in r.calls)
def test_backup_tamper_blocks_before_runtime_changes(rig):
    r=rig;(r.backup/'events.sqlite3').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='integrity'):apply_rig(r)
    assert not any(a[:3]==['systemctl','--user','stop'] for a in r.calls)
def test_busy_camera_leaves_stopped_without_auto_rollback_or_double_producer(rig):
    r=rig;r.camera['code']=0
    with pytest.raises(ValueError,match='camera'):apply_rig(r)
    assert not any(a[:3]==['systemctl','--user','start'] for a in r.calls)
    assert r.old.read_text()=='OWNER_PREVIOUS_OVERRIDE\n' and ['FAKE_ENGINE_PROBE_NOT_PHYSICAL'] not in r.calls
def test_probe_failure_does_not_install_or_start(rig):
    r=rig
    def fail(*a):raise ValueError('injected incompatible ABI')
    with pytest.raises(ValueError,match='ABI'):op.cutover(RELEASE,r.build,r.private,r.prod,r.backup,Path('/python'),r.home,True,r.runner,r.writer,fail)
    assert not any(a[:3]==['systemctl','--user','start'] for a in r.calls)
    assert not op.paths(r.home)[pf.SERVICES[1]].exists()
def test_rollback_protects_post_cutover_owner_edits(rig):
    r=rig;apply_rig(r);r.old.write_text('NEW_OWNER_WORK')
    count=len(r.calls)
    with pytest.raises(ValueError,match='owner'):op.rollback(r.backup,r.home,r.runner,r.writer)
    assert len(r.calls)==count and r.old.read_text()=='NEW_OWNER_WORK'
def test_rollback_does_not_start_changed_base_unit_under_old_label(rig):
    r=rig;apply_rig(r)
    data=it.verify_backup(r.backup)
    base=next(Path(p) for p in data['originals'] if p.endswith('for-cat-ai.service'))
    base.write_text('NEW_OWNER_BASE_UNIT')
    count=len(r.calls)
    with pytest.raises(ValueError,match='base unit'):op.rollback(r.backup,r.home,r.runner,r.writer)
    assert len(r.calls)==count and base.read_text()=='NEW_OWNER_BASE_UNIT'
def test_private_config_rejects_provider_changes_and_control_roles(rig):
    r=rig;p=r.private/'runtime.json';data=it.read(p);data['CAMERA_PROVIDER']='REAL';p.write_text(json.dumps(data))
    with pytest.raises(ValueError):cfg.validate(r.private)
def test_managed_supervisor_writer_ready_before_producer_and_peer_cleanup(monkeypatch):
    events=[];old_handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**k:types.SimpleNamespace(returncode=1,stderr=b''))
    class Child:
        def __init__(self,role):self.role=role;self.ended=False
        def poll(self):return (1 if self.role=='producer' else None) if not self.ended else 0
        def terminate(self):events.append('terminate_'+self.role);self.ended=True
        def kill(self):self.ended=True
        def wait(self,timeout):return 0
    def spawn(argv,**kwargs):
        role='writer' if 'writer' in argv else 'producer';events.append(role)
        if role=='writer':os.write(kwargs['pass_fds'][0],b'1')
        return Child(role)
    monkeypatch.setattr(runtime.subprocess,'Popen',spawn)
    monkeypatch.setattr(runtime.select,'select',lambda r,w,x,t:(r,[],[]))
    assert runtime.supervise(Path('/release'),Path('/build'),Path('/private'),Path('/prod'),{})==1
    assert events[:2]==['writer','producer'] and 'terminate_writer' in events
    assert all(signal.getsignal(s)==h for s,h in old_handlers.items())
def test_fuser_permission_or_device_error_is_not_camera_free(monkeypatch):
    with pytest.raises(ValueError,match='ownership'):op.free_camera(lambda a:{'code':1,'stderr':'Permission denied'})
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**k:types.SimpleNamespace(returncode=1,stderr=b'No such device'))
    with pytest.raises(RuntimeError,match='ownership'):runtime.supervise(Path('/r'),Path('/b'),Path('/p'),Path('/prod'),{})

def test_postverify_get_only_keeps_telemetry_physical_not_verified():
    state={'ai':{'health':'ONLINE','data_source':'REAL','simulated':False,'ai_schema_version':1,'classification':'NONE',
        'frame_metadata_available':True,'age_seconds':0,'producer_epoch':'A'},'esp32':{'connected':False},
        'safety':{'actuator_execution':False},'feed':{'actuator_execution':False}}
    camera={'status':'CAMERA_ONLINE','source':'REAL','simulated':False,'producer_epoch':'A','frame_slots':1,
        'buffered_bytes':1000,'max_viewers':4,'actuator_execution':False}
    data=pv.evaluate(state,camera,{'status':'ok'},b'Content-Type: image/jpeg\r\n\xff\xd8\xff\xd9--frame--')
    assert data['camera_api_contract']=='PASS' and data['system_acceptance']=='BLOCKED_ESP32_TELEMETRY'
    assert all(data[k]=='NOT_VERIFIED' for k in ('ESP32_TELEMETRY_PASS','JETSON_REAL_CAMERA_PASS','TAILSCALE_REMOTE_PASS','ACTUATOR_PHYSICAL_PASS'))
    assert pv.evaluate(state,{**camera,'simulated':True},{'status':'ok'},b'bad')['camera_api_contract']=='FAIL'
