"""Real C++ file replay -> temporary SQLite -> canonical readers -> ASGI -> Dart fixture.
Every exported measurement is explicitly SIMULATED; no device/network server.
"""
import asyncio
import copy
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import httpx
import pytest

HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029';BACK=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'
sys.path[:0]=[str(HERE/'candidate'),str(BACK)]
import diagnostics as d
from app.main import create_app
from app.config import HardwareConfig
from app.device_state import Esp32StateReader
from app.system_state import RealHardwareProvider
from app.ultrasonic_state import channels_view
import app.system_state as canonical
from app.camera.live_stream import FrameHub,VideoSettings
from app.camera.remote_access import RemotePolicy
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import FeedCode,Command,Frame,decode,encode
from app.storage.event_store import Event

EXE=KIT/'web_hardware/native_parser/parser_replay.exe'
VIEW={'x-forwarded-proto':'https','tailscale-user-login':'viewer@test'}
GEOMETRY={'empty_cm':110,'full_cm':30,'module_min_cm':25,'module_max_cm':400,'mount_id':'SIMULATED_TANK','owner_reviewed':True}
def wire():return json.loads((HERE/'fixtures/synthetic_wire.json').read_text())['report']
def replay(lines,tmp,chunk=7):
    path=tmp/'wire.jsonl';path.write_bytes(('\n'.join(lines)+'\n').encode())
    p=subprocess.run([str(EXE),str(path),str(chunk)],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    return [json.loads(x) for x in p.stdout.splitlines()]
def normalized(tmp):
    rows=replay([json.dumps(wire(),separators=(',',':'))],tmp)
    assert rows[-1]['accepted']==1,rows
    return rows[0]['telemetry']

@asynccontextmanager
async def api(tmp,monkeypatch,telemetry):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','REAL')
    now=[100.];path=tmp/'canonical.sqlite3';cache={'health':'ESP32_CONNECTED','serial_connected':True,
        'host_boot_id':'SYNTHETIC_BOOT','updated_monotonic_ms':100000,'last_rx_monotonic_ms':100000,
        'time_valid':False,'serial_tx_enabled':False,'actuator_execution':False,'telemetry':telemetry}
    app=create_app(db_path=path,hardware=HardwareConfig(),live_camera=FrameHub(VideoSettings()),
        remote_policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='forcat.test.ts.net',users={'viewer@test':['VIEW_CAMERA']}),scheduled_worker_enabled=False)
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
    def save():
        with sqlite3.connect(path) as db:db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)',(json.dumps(cache),))
    save();reader=Esp32StateReader(path,monotonic=lambda:now[0],boot_id='SYNTHETIC_BOOT')
    monkeypatch.setattr(canonical,'channels_view',lambda v,inventory:channels_view(v,inventory,clock=lambda:now[0]))
    provider=RealHardwareProvider(reader)
    d.mount(app,tmp/'diagnostic.sqlite3',{'execution_context':'OFFLINE_TEST_ONLY','JSN_SR04T_1':GEOMETRY},
        system_provider=provider.snapshot,bridge_provider=reader.status,clock=lambda:now[0])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='https://forcat.test.ts.net') as client:
            yield app,client,cache,now,save

@pytest.mark.parametrize('chunk',[1,7,127,8192])
def test_synthetic_full_payload_through_actual_cpp_fragments(tmp_path,chunk):
    line=json.dumps(wire(),separators=(',',':'));assert len(line)>4096
    rows=replay([line],tmp_path,chunk);assert rows[-1]['accepted']==1
    t=rows[0]['telemetry'];assert t['mode']=='diag_current_hardware' and t['diagnostic_profile']=='diag_four_ultrasonic'
    assert len(t['ultrasonic'])==4 and t['sensors']['button']['request_count']==1
    assert t['sensors']['hx711']['firmware_value_grams']==34.981

@pytest.mark.parametrize('extra,expected',[(0,1),(1,0)])
def test_frame_exact_boundary_is_not_truncated(tmp_path,extra,expected):
    line=json.dumps(wire(),separators=(',',':'));line+=' '*(8192-len(line)+extra)
    rows=replay([line],tmp_path,127);assert rows[-1]['accepted']==expected
    assert rows[-1]['oversized']==extra

@pytest.mark.parametrize('fault',['mode','profile','schema','missing_weight','missing_button','pin','duplicate_key','malformed','unsafe','weight_invalid'])
def test_rejected_wire_never_becomes_accepted_sensor_data(tmp_path,fault):
    x=wire()
    if fault=='mode':x['mode']='diag_four_ultrasonic'
    elif fault=='profile':x['kit_profile']='OTHER'
    elif fault=='schema':x['telemetry_schema_version']=3
    elif fault=='missing_weight':del x['weight']
    elif fault=='missing_button':del x['current_hardware']['manual_button_request_count']
    elif fault=='pin':x['ultrasonic']['HC_SR04_2']['echo_gpio']=6
    elif fault=='unsafe':x['current_hardware']['pump_armed']=True
    elif fault=='weight_invalid':x['weight']['value_grams']=None
    line=json.dumps(x,separators=(',',':'))
    if fault=='duplicate_key':line='{"mode":"HX711_REFERENCE",'+line[1:]
    if fault=='malformed':line=line[:-8]
    rows=replay([line],tmp_path);assert rows[-1]['accepted']==0

def test_cpp_to_sqlite_api_exports_actual_contract_cases(monkeypatch,tmp_path):
    async def go():
        async with api(tmp_path,monkeypatch,normalized(tmp_path)) as (app,c,cache,now,save):
            cases={}
            async def capture(name):
                response=await c.get('/api/v1/hardware-diagnostics/status',headers=VIEW)
                assert response.status_code==200,response.text
                value=response.json();assert value['source']=='SIMULATED' and value['simulated'] is True
                cases[name]=value;return value
            v=await capture('healthy')
            for sid,cm in [('HC_SR04_1',15),('HC_SR04_2',45),('JSN_SR04T_1',50),('JSN_SR04T_2',75)]:
                assert v['ultrasonic'][sid]['state']=='OK' and v['ultrasonic'][sid]['distance_cm']==cm
            assert v['pir']['motion'] is True and v['hx711']['grams']==34.981
            assert v['oled']['health']=='HEALTHY' and v['button']['pressed'] is True and v['button']['request_count']==1
            assert v['ultrasonic']['JSN_SR04T_1']['water_level']['percent']==75
            assert v['ultrasonic']['JSN_SR04T_2']['water_level']['percent'] is None
            assert v['buzzer']['available'] is False
            now[0]=102.1;v=await capture('stale')
            assert all(s['distance_cm'] is None and s['state']=='STALE' for s in v['ultrasonic'].values())
            assert v['pir']['motion'] is None and v['hx711']['grams'] is None
            now[0]=100;cache.update(health='ESP32_DISCONNECTED',serial_connected=False);save();v=await capture('disconnected')
            assert all(s['state']=='DISCONNECTED' and s['distance_cm'] is None for s in v['ultrasonic'].values())
            cache.update(health='ESP32_BAD_TELEMETRY',serial_connected=True);save();v=await capture('invalid')
            assert all(s['state']=='INVALID' and s['distance_cm'] is None for s in v['ultrasonic'].values())
            cache.update(health='ESP32_CONNECTED');raw=wire();s=raw['ultrasonic']['HC_SR04_2']
            s.update(valid=False,timeout=True,state='TIMEOUT',distance_cm=None,measurement_state='NO_ECHO')
            cache['telemetry']=replay([json.dumps(raw,separators=(',',':'))],tmp_path)[0]['telemetry'];save();v=await capture('timeout')
            assert v['ultrasonic']['HC_SR04_2']['state']=='TIMEOUT' and v['ultrasonic']['HC_SR04_2']['distance_cm'] is None
            # The read-only bridge mode must never dispatch even a mock feed.
            assert (await c.post('/api/v1/feed/manual',headers=VIEW)).status_code in (403,503)
            assert app.state.transport.feeds=={}
            (HERE/'fixtures/api_contract.json').write_text(json.dumps({'source':'SIMULATED','execution_context':'OFFLINE_TEST_ONLY','physical_pass':False,'cases':cases},indent=2)+'\n')
    asyncio.run(go())

def test_exported_contract_time_domains_and_error_reasons():
    fixture=json.loads((HERE/'fixtures/api_contract.json').read_text())
    cases=fixture['cases'];healthy=cases['healthy'];stale=cases['stale']
    assert healthy['telemetry_time']=={'clock_domain':'HOST_MONOTONIC_MS','last_rx_ms':100000,'age_ms':0,'device_uptime_ms':70000,'is_UTC_timestamp':False}
    assert stale['telemetry_time']['age_ms']>2000
    assert stale['ultrasonic']['HC_SR04_1']['sample_age_ms']>2000
    for name,state in [('stale','STALE'),('invalid','INVALID'),('disconnected','DISCONNECTED')]:
        assert cases[name]['ultrasonic']['HC_SR04_1']['reason']==state
    assert cases['timeout']['ultrasonic']['HC_SR04_2']['reason']=='TIMEOUT'
    assert healthy['ultrasonic']['HC_SR04_1']['reason'] is None

def test_actual_cpp_session_timeline_through_cached_api(monkeypatch,tmp_path):
    timeline=json.loads((HERE/'fixtures/session_timeline.json').read_text())
    async def go():
        async with api(tmp_path,monkeypatch,timeline[0]['telemetry']) as (_,c,cache,now,save):
            path=HERE/'fixtures/api_contract.json'
            fixture=json.loads(path.read_text()) if path.exists() else {'source':'SIMULATED','execution_context':'OFFLINE_TEST_ONLY','physical_pass':False,'cases':{}}
            for step in timeline:
                now[0]=step['at_ms']/1000
                cache.update(health=step['health'],serial_connected=step['serial_connected'],
                    updated_monotonic_ms=step['at_ms'],last_rx_monotonic_ms=step['last_rx_ms'],telemetry=step['telemetry'])
                save();v=(await c.get('/api/v1/hardware-diagnostics/status',headers=VIEW)).json()
                expected={'ESP32_CONNECTED':'OK','ESP32_STALE':'STALE','ESP32_DISCONNECTED':'DISCONNECTED','ESP32_BAD_TELEMETRY':'INVALID'}[step['health']]
                assert v['ultrasonic']['HC_SR04_1']['state']==expected
                if expected!='OK':
                    assert v['ultrasonic']['HC_SR04_1']['distance_cm'] is None and v['hx711']['grams'] is None
                if step['case'] in ('duplicate_frozen','reconnect_waiting','unsafe_latched'):fixture['cases'][step['case']]=v
            path.write_text(json.dumps(fixture,indent=2)+'\n')
    asyncio.run(go())

@pytest.mark.parametrize('scenario',['overshoot','TIMEOUT','HX_TIMEOUT','INVALID','DISCONNECT','NO_PROGRESS'])
def test_cpp_closed_loop_failure_never_becomes_api_success(monkeypatch,tmp_path,scenario):
    outcome=json.loads((HERE/'fixtures/dispense_outcomes.json').read_text())[scenario]
    assert outcome['state']=='FAULT' and outcome['source']=='SIMULATED'
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','0');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','MOCK')
        transport=MockEsp32Transport()
        app=create_app(db_path=tmp_path/'failure.sqlite3',hardware=HardwareConfig(),transport=transport,
            live_camera=FrameHub(VideoSettings()),remote_policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='forcat.test.ts.net',
                users={'engineer@test':['VIEW_CAMERA','FEED_MANUAL']}),scheduled_worker_enabled=False)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='https://forcat.test.ts.net',
                headers={'x-forwarded-proto':'https','tailscale-user-login':'engineer@test'}) as c:
                response=await c.post('/api/v1/feed/manual',headers={'Idempotency-Key':'SIM_'+scenario})
                assert response.status_code==202,response.text
                receipt=response.json();assert receipt['state']=='PENDING'
                transport.complete_feed(receipt['request_id'],FeedCode.ERROR)
                response=await c.get('/api/v1/status');assert response.status_code==200,response.text
                status=response.json();assert status['feeds'][0]['state']=='ERROR'
                sessions=(await c.get('/api/v1/sessions/feeding')).json()
                assert len(sessions)==1 and sessions[0]['result']=='ERROR' and sessions[0]['source']=='MOCK'
    asyncio.run(go())

def test_mock_manual_feed_ack_final_duplicate_disconnect_and_histories(monkeypatch,tmp_path):
    class AckInsteadOfFinal(MockEsp32Transport):
        ack_only=True
        def exchange(self,packet):
            frame=decode(packet)
            if self.online and self.ack_only and frame.command==Command.FEED_STATUS:
                return encode(Frame(frame.request_id,Command.ACK,bytes([Command.FEED_STATUS])))
            return super().exchange(packet)
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','0');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','MOCK')
        t=AckInsteadOfFinal();app=create_app(db_path=tmp_path/'mock.sqlite3',hardware=HardwareConfig(),transport=t,
            live_camera=FrameHub(VideoSettings()),remote_policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='forcat.test.ts.net',
                users={'engineer@test':['VIEW_CAMERA','FEED_MANUAL']}),scheduled_worker_enabled=False)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='https://forcat.test.ts.net',
                headers={'x-forwarded-proto':'https','tailscale-user-login':'engineer@test'}) as c:
                response=await c.post('/api/v1/feed/manual',headers={'Idempotency-Key':'SYNTHETIC_MANUAL_35G'})
                assert response.status_code==202,response.text
                first=response.json()
                assert first['state']=='PENDING',first
                duplicate=(await c.post('/api/v1/feed/manual',headers={'Idempotency-Key':'SYNTHETIC_MANUAL_35G'})).json()
                assert duplicate==first and len(t.feeds)==1
                assert (await c.get('/api/v1/status')).json()['feeds'][0]['state']=='PENDING'
                t.online=False;offline=(await c.get('/api/v1/status')).json()
                assert offline['feeds'][0]['state']=='PENDING' and offline['esp32_online'] is False
                assert (await c.get('/api/v1/sessions/feeding')).json()==[]
                outcomes=json.loads((HERE/'fixtures/dispense_outcomes.json').read_text())
                assert outcomes['nominal']['state']=='COMPLETE' and outcomes['nominal']['dispensed_grams']==35
                t.online=True;t.ack_only=False;t.complete_feed(first['request_id'],FeedCode.SUCCESS)
                final=(await c.get('/api/v1/status')).json()['feeds'][0]
                assert final['state']=='SUCCESS'
                sessions=(await c.get('/api/v1/sessions/feeding')).json();assert len(sessions)==1 and sessions[0]['source']=='MOCK'
                assert (await c.get('/api/v1/drinking-history')).json()==[]
                app.state.store.append(Event(kind='DRINKING',state='SIMULATED_OBSERVATION',details={'source':'MOCK','simulated':True,'volume_ml':None}))
                water=(await c.get('/api/v1/drinking-history')).json();assert len(water)==1 and water[0]['details']['volume_ml'] is None
                fixture={'source':'SIMULATED','execution_context':'OFFLINE_TEST_ONLY','physical_pass':False,
                    'ack':first,'after_disconnect':offline['feeds'][0],'final':final,
                    'feeding_history':(await c.get('/api/v1/feeding-history')).json(),'drinking_history':water,'feeding_sessions':sessions}
                (HERE/'fixtures/feed_contract.json').write_text(json.dumps(fixture,indent=2)+'\n')
    asyncio.run(go())
