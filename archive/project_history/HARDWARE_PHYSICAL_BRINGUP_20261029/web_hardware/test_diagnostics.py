"""Current app reused in ASGI, fake state/executor only; NO device/camera/UART."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sqlite3
import sys
import types
import httpx
import pytest
HERE=Path(__file__).resolve().parent;KIT=HERE.parent;ROOT=KIT.parent
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'));sys.path.insert(0,str(HERE));sys.path.insert(0,str(KIT/'tools'))
import diagnostics as d
from completed_backup_pair import validate_pair
from physical_acceptance import inspect_contents
from image_layout import sha
from app.main import create_app
from app.config import HardwareConfig
from app.camera.live_stream import FrameHub,VideoSettings
from app.camera.remote_access import RemotePolicy

CAP={'profile':'manual_buzzer_sensor_diag_v1','gpio':2,'polarity':'ACTIVE_LOW','vcc':3.3,'manual_only':True,
    'auto_off_ms':600,'max_tests_per_boot':3,'cooldown_ms':60000}
def state():
    return {'data_source':'REAL','esp32':{'connected':True,'health':'ESP32_CONNECTED'},
        'safety':{'actuator_execution':False,'actuator_outputs_enabled':0,'servo_armed':False,'pump_armed':False,'auto_feed':False,'auto_water':False},
        'ai':{'classification':'CAT','health':'ONLINE','confidence':.9,'data_source':'REAL','simulated':False},
        'ultrasonic':{key:{'trigger_gpio':pins[0],'echo_gpio':pins[1],'valid':True,'enabled':True,'timeout':False,'stale':False,
            'state':'HEALTHY','distance_cm':50,'sample_age_ms':0} for key,pins in d.CHANNELS.items()},
        'weight':{'calibrated':False,'calibration_valid':False,'grams':None,'raw_counts':-700000}}
def bridge():
    return {'health':'ESP32_CONNECTED','telemetry_usable_now':True,'last_rx_monotonic_ms':100000,
        'telemetry':{'mode':'diag_current_hardware','sensors':{'pir':{'qualified_fields_available':True,'motion_valid':True,
            'motion_quality':'VALID','motion_stable':True},'hx711':{'firmware_observation_valid':True,
            'firmware_value_grams':34.981,'firmware_age_at_frame_ms':0}}}}
GEOMETRY={'empty_cm':110,'full_cm':30,'module_min_cm':25,'module_max_cm':400,'mount_id':'TEST_ONLY','owner_reviewed':True}
class Executor:
    def __init__(self,clock):self.clock=clock;self.ids=[];self.off_at=None
    def start_fixed_sequence(self,identity):self.ids.append(identity);self.off_at=self.clock()+.6
    def active(self):return self.off_at is not None and self.clock()<self.off_at
@asynccontextmanager
async def api(tmp,monkeypatch,enabled=False):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','REAL')
    now=[100.];s=state();b=bridge();executor=Executor(lambda:now[0]);service=d.BuzzerContract(executor if enabled else None,enabled,lambda:now[0])
    if enabled:b['telemetry']['manual_buzzer_capability']=dict(CAP)
    app=create_app(db_path=tmp/'canonical.sqlite3',hardware=HardwareConfig(),live_camera=FrameHub(VideoSettings()),
        remote_policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='forcat.test.ts.net',users={
            'viewer@test':['VIEW_CAMERA'],'engineer@test':['VIEW_CAMERA','CONTROL_SYSTEM']}),scheduled_worker_enabled=False)
    handles=d.mount(app,tmp/'diagnostic_only.sqlite3',{'execution_context':'OFFLINE_TEST_ONLY','FOOD_ROI':{'mode':'FULL_FRAME','region':None,'reviewed':False},'JSN_SR04T_1':GEOMETRY},
        service,lambda:s,lambda:b,lambda:now[0])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='https://forcat.test.ts.net') as client:
            yield app,client,s,b,now,executor,handles
VIEW={'x-forwarded-proto':'https','tailscale-user-login':'viewer@test'}
ADMIN={**VIEW,'tailscale-user-login':'engineer@test'}
BODY={'request_id':'one','confirm':'BUZZER_GPIO2_ACTIVE_LOW_3V3_REVIEWED'}
def test_owner_completed_actual_files_verified_readonly_no_old_exitcodes():
    folder=ROOT/'ESP32_FULL_BACKUP_20261029';a=folder/'esp32s3_flash_16mb.bin';b=folder/'esp32s3_flash_16mb_B.bin'
    before=[(p.stat().st_size,p.stat().st_mtime_ns) for p in (a,b)]
    r=validate_pair(a,b,'56A04D58BD8063E64F6B043A6B91D2D412C64D75E563EE58D81A83666D9A8E16')
    assert r['backup_AB_file_integrity']=='PASS' and not r['third_read_required'] and not r['old_exitcode_requested']
    assert before==[(p.stat().st_size,p.stat().st_mtime_ns) for p in (a,b)]
@pytest.mark.parametrize('failure',['same_file','different_bytes'])
def test_completed_pair_validation_is_fail_closed_for_bad_pair(tmp_path,failure):
    a=tmp_path/'SYNTHETIC_A.bin';a.write_bytes(b'\xff'*16777216)
    if failure=='same_file':
        with pytest.raises(ValueError,match='independent'):validate_pair(a,a,sha(a))
    else:
        b=tmp_path/'SYNTHETIC_B.bin';b.write_bytes(b'\x00'*16777216)
        with pytest.raises(ValueError,match='SHA mismatch'):validate_pair(a,b,sha(a))
def test_actual_backup_static_layout_and_runtime_bank_scopes():
    report=json.loads((HERE/'backup_and_contract_review.json').read_text())
    assert report['layout_matches_new_sensor_build'] and report['rollback_local_image_extraction']=='PASS'
    assert report['runtime_boot_bank'].startswith('NOT_VERIFIED') and report['flash_authorized'] is False
    table=report['actual_flash_analysis']['partition_candidates'][0]
    assert table['table_offset']==0x8000 and table['apps'][0]['offset']==0x10000
    assert table['apps'][0]['used_image_sha256']=='820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826'
    assert table['apps'][1]['partition_all_ff'] is True
@pytest.mark.parametrize('mutation',[{'full_cm':0},{'empty_cm':20},{'owner_reviewed':False},{'mount_id':''},{'module_min_cm':60}])
def test_bad_geometry_cannot_invent_water_level(mutation):
    assert d.water_level(50,{**GEOMETRY,**mutation})['percent'] is None
def test_actual_config_only_and_invalid_distance_not_zero_level():
    assert d.water_level(50,GEOMETRY)['percent']==75
    assert d.water_level(None,GEOMETRY)['percent'] is None
    assert d.water_level(200,GEOMETRY)['percent'] is None
    assert d.water_level(50,None)['state']=='NOT_CONFIGURED'
def test_snapshot_four_channels_qualified_pir_and_observation_only_grams():
    r=d.snapshot(state(),bridge(),FrameHub(),{'JSN_SR04T_1':GEOMETRY},d.BuzzerContract(),lambda:100)
    assert len(r['ultrasonic'])==4 and r['ultrasonic']['JSN_SR04T_1']['water_level']['percent']==75
    assert r['ultrasonic']['JSN_SR04T_2']['water_level']['percent'] is None
    assert r['pir']['motion'] is True and r['hx711']['grams']==34.981 and 'PERSISTENCE_NOT_VERIFIED' in r['hx711']['authority']
    assert 'WATER_ROI' not in r and not r['buzzer']['available'] and r['servo']==r['pump']=='LOCKED'
@pytest.mark.parametrize('condition',['stale','warmup','legacy','invalid_sensor','wrong_pins','unknown_hx_context'])
def test_failure_inputs_are_not_presented_as_good(condition):
    s=state();b=bridge();now=100
    if condition=='stale':now=104
    if condition=='warmup':b['telemetry']['sensors']['pir'].update(motion_quality='WARMING_UP',motion_valid=False,motion_stable=None)
    if condition=='legacy':b['telemetry']['sensors']['pir']={'motion':True,'configured':True}
    if condition=='invalid_sensor':s['ultrasonic']['HC_SR04_1'].update(valid=False,timeout=True,state='TIMEOUT',distance_cm=None)
    if condition=='wrong_pins':s['ultrasonic']['HC_SR04_1']['echo_gpio']=17
    if condition=='unknown_hx_context':b['telemetry']['sensors']['hx711']['firmware_observation_valid']=False
    r=d.snapshot(s,b,FrameHub(),{},d.BuzzerContract(),lambda:now)
    if condition in ('stale','warmup','legacy'):assert r['pir']['motion'] is None
    if condition in ('stale','invalid_sensor','wrong_pins'):assert r['ultrasonic']['HC_SR04_1']['distance_cm'] is None
    if condition in ('stale','unknown_hx_context'):assert r['hx711']['grams'] is None
    assert r['hx711']['static_measurement_physical_pass']=='YES_OWNER_ACCEPTED'
def test_routes_permissions_and_unsupported_buzzer_never_send(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,s,b,now,e,h):
            assert (await c.get('/api/v1/hardware-diagnostics/status')).status_code==403
            response=await c.get('/api/v1/hardware-diagnostics/status',headers=VIEW)
            assert response.status_code==200 and not response.json()['permissions']['CONTROL_SYSTEM']
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=VIEW,json=BODY)).status_code==403
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)).status_code==409
            assert e.ids==[] and app.state.transport.feeds=={}
            assert (await c.get('/api/v1/health',headers=VIEW)).status_code==200
            assert (await c.post('/api/v1/feed/manual',headers=ADMIN)).status_code==403 # CONTROL_SYSTEM is not FEED_MANUAL
    asyncio.run(go())
def test_fake_buzzer_fixed_sequence_timeout_idempotency_cooldown_no_physical_pass(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch,True) as (_,c,s,b,now,e,h):
            first=await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)
            assert first.status_code==200 and first.json()['status']=='REQUEST_RECEIVED_NOT_ACOUSTIC_PASS'
            assert e.active() and len(e.ids)==1
            again=await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)
            assert again.json()==first.json() and len(e.ids)==1
            now[0]+=.6;assert not e.active()
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json={**BODY,'request_id':'two'})).status_code==429
            assert first.json()['physical_result']=='NOT_VERIFIED' and first.json()['feed_success'] is False
    asyncio.run(go())
def test_link_loss_and_capability_injection_body_cannot_start_buzzer(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch,True) as (_,c,s,b,now,e,h):
            b['telemetry_usable_now']=False
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)).status_code==409
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json={**BODY,'gpio':7,'duration_ms':9999})).status_code==422
            assert e.ids==[]
    asyncio.run(go())
def test_unsafe_or_unknown_safety_telemetry_never_enables_test(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch,True) as (_,c,s,b,now,e,h):
            s['safety']['servo_armed']=True
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)).status_code==409
            s['safety']={}
            assert (await c.post('/api/v1/hardware-diagnostics/buzzer-test',headers=ADMIN,json=BODY)).status_code==409
            assert not e.ids
    asyncio.run(go())
def test_unknown_transport_outcome_consumes_identity_not_duplicate_retry():
    class Broken:
        calls=0
        def start_fixed_sequence(self,_):self.calls+=1;raise OSError('fake uncertain ACK')
    e=Broken();b=d.BuzzerContract(e,True,lambda:100)
    assert b.request('one')['status']=='TRANSPORT_RESULT_UNKNOWN_DO_NOT_REPEAT'
    assert b.request('one')['status']=='TRANSPORT_RESULT_UNKNOWN_DO_NOT_REPEAT' and e.calls==1
def test_bounded_observation_journal_not_canonical_db(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,s,b,now,e,h):
            assert (await c.post('/api/v1/hardware-diagnostics/observations',headers=VIEW,json={'sensor_id':'PIR','USER_OBSERVED':'walk'})).status_code==403
            assert (await c.post('/api/v1/hardware-diagnostics/observations',headers=ADMIN,json={'sensor_id':'PIR','USER_OBSERVED':'OWNER_TEST_NOT_AUTO_PASS'})).status_code==200
            for n in range(270):h['journal'].add('USER_OBSERVED',{'USER_OBSERVED':str(n)})
            with sqlite3.connect(h['journal'].path) as db:assert db.execute('SELECT COUNT(*) FROM hardware_test_events').fetchone()[0]==256
            rows=(await c.get('/api/v1/hardware-diagnostics/events',headers=VIEW)).json()
            assert len(rows)==50 and all(r['physical_result']=='NOT_VERIFIED' for r in rows)
            with pytest.raises(ValueError):d.mount(app,app.state.store_path)
    asyncio.run(go())
def test_bridge_candidate_bound_and_guards_without_claiming_native_build():
    text=(HERE/'bridge_candidate/telemetry.h').read_text()
    original=(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/device/telemetry.h').read_text()
    assert 'line.size()>TELEMETRY_MAX_LINE' in text and 'line_.size()==TELEMETRY_MAX_LINE' in text and 'TELEMETRY_MAX_LINE=8192' in text
    assert 'line.size()>4096' in original # original source unchanged
    assert 'if(mode!="diag_current_hardware")' in text
    for guard in ('ACTUATOR_SAFETY_VIOLATION','UNEXPECTED_ACTUATOR_MODE','hardware_verified','json_tokener_new_ex(16)','rejectDuplicateKeys(line)'):
        assert guard in text and guard in original
    assert 'motion_stable' in text and 'OBSERVATION_ONLY_NOT_FEED_AUTHORITY' in text
def test_host_age_not_last_channel_age_controls_pir_and_hx():
    r=d.snapshot(state(),bridge(),FrameHub(),{},d.BuzzerContract(),lambda:102.5)
    assert r['pir']['motion'] is None and r['hx711']['grams'] is None
    assert all(s['distance_cm'] is None for s in r['ultrasonic'].values())
def test_jsn2_role_tbd_blocks_level_even_with_copied_geometry():
    r=d.snapshot(state(),bridge(),FrameHub(),{'JSN_SR04T_2':GEOMETRY},d.BuzzerContract(),lambda:100)
    s=r['ultrasonic']['JSN_SR04T_2'];assert s['role']=='TBD' and s['water_level']['percent'] is None
    assert s['water_level']['state']=='ROLE_TBD_LEVEL_DISABLED'
def test_timeout_sensor_error_and_disconnect_are_distinct():
    s=state();b=bridge();s['ultrasonic']['HC_SR04_1'].update(valid=False,timeout=True,state='TIMEOUT',distance_cm=None)
    s['ultrasonic']['JSN_SR04T_1'].update(valid=False,state='UNKNOWN',measurement_state='OUT_OF_RANGE',distance_cm=None)
    r=d.snapshot(s,b,FrameHub(),{},d.BuzzerContract(),lambda:100)
    assert r['ultrasonic']['HC_SR04_1']['state']=='TIMEOUT'
    assert r['ultrasonic']['JSN_SR04T_1']['state']=='SENSOR_ERROR'
    s['esp32'].update(connected=False,health='ESP32_DISCONNECTED')
    r=d.snapshot(s,b,FrameHub(),{},d.BuzzerContract(),lambda:100)
    assert r['ultrasonic']['HC_SR04_1']['state']=='DISCONNECTED'
def test_log_export_is_get_only_bounded_and_not_physical_pass(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch) as (_,c,s,b,now,e,h):
            h['journal'].add('USER_OBSERVED',{'USER_OBSERVED':'TEST_ONLY'})
            r=await c.get('/api/v1/hardware-diagnostics/events/export',headers=VIEW)
            assert r.status_code==200 and 'attachment' in r.headers['content-disposition']
            assert r.json()['kind']=='BOUNDED_HARDWARE_TEST_LOG_EXPORT' and r.json()['physical_pass'] is False
            assert len(r.json()['events'])==1 and not e.ids
    asyncio.run(go())
def test_actual_cpp_output_through_sqlite_reader_provider_and_api(monkeypatch,tmp_path):
    import subprocess
    from app.device_state import Esp32StateReader
    from app.system_state import RealHardwareProvider
    from app.ultrasonic_state import channels_view
    import app.system_state as canonical
    exe=HERE/'native_parser/parser_replay.exe'
    assert exe.is_file(),'Run actual C++ parser tests before integration'
    p=subprocess.run([str(exe),str(KIT/'test_output/quad_firmware_loop_test.log'),'7'],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    telemetry=[json.loads(line)['telemetry'] for line in p.stdout.splitlines() if json.loads(line).get('event')=='ACCEPTED_SOFTWARE_REPLAY'][-1]
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,s,b,now,e,h):
            path=Path(app.state.store_path)
            cache={'health':'ESP32_CONNECTED','serial_connected':True,'host_boot_id':'TEST_BOOT',
                'updated_monotonic_ms':100000,'last_rx_monotonic_ms':100000,'time_valid':False,
                'serial_tx_enabled':False,'actuator_execution':False,'telemetry':telemetry}
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE IF NOT EXISTS esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
                db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)',(json.dumps(cache),))
            reader=Esp32StateReader(path,monotonic=lambda:100,boot_id='TEST_BOOT')
            monkeypatch.setattr(canonical,'channels_view',lambda value,inventory:channels_view(value,inventory,clock=lambda:100))
            provider=RealHardwareProvider(reader)
            s.clear();s.update(provider.snapshot());b.clear();b.update(reader.status())
            r=await c.get('/api/v1/hardware-diagnostics/status',headers=VIEW)
            assert r.status_code==200,r.text
            body=r.json();assert body['execution_context']=='OFFLINE_TEST_ONLY'
            assert body['ultrasonic']['HC_SR04_1']['distance_cm']>35
            assert body['pir']['quality']=='WARMING_UP' and body['pir']['motion'] is None
            assert body['button']['gpio']==21 and body['button']['request_count']==0
            assert body['oled']['health']=='NOT_CONNECTED' and body['buzzer']['available'] is False
            assert not e.ids and app.state.transport.feeds=={}
    asyncio.run(go())
def test_arm64_tool_defaults_to_plan_and_rejects_execution_on_windows(tmp_path):
    import subprocess
    p=subprocess.run([sys.executable,'-B',str(HERE/'native_arm64_check.py')],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    plan=json.loads(p.stdout);assert plan['mode']=='PLAN_ONLY' and plan['ARM64_NATIVE_TEST_PASS']=='NOT_RUN'
    assert not plan['serial_opened'] and not plan['camera_opened']
    if sys.platform=='win32':
        p=subprocess.run([sys.executable,'-B',str(HERE/'native_arm64_check.py'),'--execute','BUILD_AND_FILE_REPLAY_ONLY','--out',str(tmp_path/'unused')],capture_output=True,text=True,timeout=30)
        assert p.returncode!=0 and 'requires Linux ARM64' in p.stderr and not (tmp_path/'unused').exists()
def test_owner_arm64_replay_harness_with_actual_windows_parser_not_arm_acceptance(tmp_path):
    import native_arm64_check
    cases=native_arm64_check.replay(HERE/'native_parser/parser_replay.exe',tmp_path)
    assert len(cases)==26 and 'unsafe_latch' in cases and 'oversized_8193' in cases
