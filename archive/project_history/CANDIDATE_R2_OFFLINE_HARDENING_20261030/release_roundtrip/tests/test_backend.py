"""Connected native-file -> temporarySQLite -> real reader/provider -> ASGI.
Transport I/O, deterministic service clock and AI are explicitly labelled adapters.
"""
import asyncio,json,math,os,sqlite3,sys
from contextlib import closing,asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import httpx,pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'candidate/backend'),str(ROOT/'candidate')]
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
from app.serial_link.protocol import FeedCode
from app.storage.repositories import RecordRepository
from app.storage.event_store import Event
from app.feeding_mass import in_band,POLICY
OUTPUT=Path(os.environ['HARDENING_OUTPUT'])
HEAD={'x-forwarded-proto':'https','tailscale-user-login':'synthetic@test'}
def policy():return RemotePolicy(mode='TAILSCALE_SERVE',hostname='forcat.test.ts.net',users={'synthetic@test':['VIEW_CAMERA','CONTROL_SYSTEM','FEED_MANUAL']})
def make_app(path,transport=None,reader=None,max_events=1000):
    return create_app(db_path=path,hardware=HardwareConfig(),transport=transport,live_camera=FrameHub(VideoSettings()),
        remote_policy=policy(),scheduled_worker_enabled=False,max_events=max_events,simulation_feed_results=reader)
@asynccontextmanager
async def client(app):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1)),base_url='https://forcat.test.ts.net',headers=HEAD) as c:yield c
class LabelledReader(Esp32StateReader):
    def status(self):return {**super().status(),'source':'SIMULATED','simulated':True}

def test_connected_native_sqlite_fastapi_fixture(monkeypatch,tmp_path):
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','REAL')
        rows=json.loads((ROOT/'evidence/native_core/stream_records.json').read_text());clock=[100.];ai={'classification':'UNKNOWN','age_seconds':0}
        path=tmp_path/'canonical.sqlite3';app=make_app(path)
        with closing(sqlite3.connect(path)) as db:
            with db:db.execute('CREATE TABLE esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
        reader=LabelledReader(path,monotonic=lambda:clock[0],boot_id='SYNTHETIC_BOOT_A')
        provider=RealHardwareProvider(reader)
        monkeypatch.setattr(canonical,'channels_view',lambda v,inventory:channels_view(v,inventory,clock=lambda:clock[0]))
        def system():
            v=provider.snapshot();v['data_source']='MOCK'
            v['ai']={**ai,'health':'ONLINE','source':'SIMULATED','data_source':'SIMULATED','simulated':True}
            return v
        class ClockService:
            async def start(self):pass
            async def stop(self):pass
            def snapshot(self):return system()
        app.state.esp32_reader=reader;app.state.system_state=ClockService()
        handles=d.mount(app,tmp_path/'journal.sqlite3',{'execution_context':'OFFLINE_TEST_ONLY'},system_provider=system,bridge_provider=reader.status,clock=lambda:clock[0])
        cases={}
        async with client(app) as c:
            for row in rows:
                name=row['case'];clock[0]=row['updated_monotonic_ms']/1000
                ai.update(classification={'healthy_cat':'CAT','progress_dog':'DOG','recovered_none':'NONE'}.get(name,'UNKNOWN'),age_seconds=0)
                if name=='ai_unknown':ai.update(classification='CAT',age_seconds=2)
                cache={**row,'host_boot_id':'OLD_SYNTHETIC_BOOT' if name=='wrong_host_boot' else 'SYNTHETIC_BOOT_A',
                    'time_valid':False,'serial_tx_enabled':False,'actuator_execution':False}
                with closing(sqlite3.connect(path)) as db:
                    with db:db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)',(json.dumps(cache),))
                handles['journal'].add('NATIVE_SIMULATED_STATE',{'event_id':name,'source':'SIMULATED','health':row['health']})
                app.state.store.append(Event(kind='SYNTHETIC_LINK',state=row['health'],details={'source':'SIMULATED','case':name}))
                r=await c.get('/api/v1/hardware-diagnostics/status');assert r.status_code==200,r.text
                v=r.json();assert v['source']=='SIMULATED' and v['simulated'] is True
                assert v['feeding_mass_policy']['tolerance_grams']==5
                cases[name]=v
                if name in ('partial','duplicate_frozen','out_of_order','host_clock_backwards','truncated_json','disconnect','reconnect_waiting','timeout','wrong_host_boot','unsafe','unsafe_after_good','unsafe_still_latched','restart_history_not_live'):
                    assert all(x['distance_cm'] is None for x in v['ultrasonic'].values()),name
                if name=='healthy_cat':
                    assert v['hx711']['grams']==34.981 and v['button']['request_count']==1 and v['oled']['initialized'] is True
                if name in ('healthy_cat','progress_dog','recovered_none'):assert v['ai']['classification']==ai['classification']
                if name=='ai_unknown':assert v['ai']['classification']=='UNKNOWN'
            assert len((await c.get('/api/v1/hardware-diagnostics/events')).json())==len(rows)
            assert len((await c.get('/api/v1/events')).json())==len(rows)
            assert (await c.get('/api/v1/feeding-history')).json()==[]
            assert (await c.get('/api/v1/drinking-history')).json()==[]
            assert (await c.post('/api/v1/feed/manual')).status_code==503
        (OUTPUT/'e2e_api.json').write_text(json.dumps({'source':'SIMULATED','physical_pass':False,'cases':cases},indent=2)+'\n')
    asyncio.run(go())

def projected_mass(row):
    mass=row['requested_fixture_final']
    actual=row['actual_dispensed_grams'] if row['state']=='COMPLETE' or (mass==29 and row['actual_dispensed_grams']==29) else None
    return {'source':'SIMULATED','physical_pass':False,'state':row['state'],'actual_dispensed_grams':actual,'latest_observed_grams':mass}
@pytest.mark.parametrize('mass',[29,30,35,36,38,40,41])
def test_native_mass_to_final_status_history_and_restart(monkeypatch,tmp_path,mass):
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','0');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','MOCK')
        row=next(x for x in json.loads((ROOT/'evidence/native_core/mass_outcomes.json').read_text()) if x['requested_fixture_final']==mass)
        meta=projected_mass(row);path=tmp_path/'mass.sqlite3';t=MockEsp32Transport();reader=lambda _:meta
        app=make_app(path,t,reader)
        async with client(app) as c:
            response=await c.post('/api/v1/feed/manual',headers={'Idempotency-Key':'SIM_MASS_'+str(mass)});assert response.status_code==202,response.text
            ack=response.json();assert ack['state']=='PENDING' and ack['actual_dispensed_grams'] is None and ack['final_status_received'] is False
            t.online=False;assert (await c.get('/api/v1/status')).json()['feeds'][0]['state']=='PENDING';t.online=True
            expected='SUCCESS' if row['state']=='COMPLETE' else 'ERROR'
            t.complete_feed(ack['request_id'],FeedCode[expected])
            final=(await c.get('/api/v1/status')).json()['feeds'][0]
            assert final['state']==expected and final['final_status_received'] is True
            assert final['actual_dispensed_grams']==meta['actual_dispensed_grams']
            assert final['latest_observed_grams']==mass and final['mass_policy']['tolerance_grams']==5
            assert len((await c.get('/api/v1/sessions/feeding')).json())==1
            assert (await c.post('/api/v1/feed/manual',headers={'Idempotency-Key':'SIM_MASS_'+str(mass)})).json()==final
            (OUTPUT/('mass_'+str(mass)+'.json')).write_text(json.dumps({'source':'SIMULATED','physical_pass':False,'ack':ack,'final':final,'native':row},indent=2)+'\n')
        resumed=make_app(path,t,reader)
        async with client(resumed) as c:
            restarted=(await c.get('/api/v1/feed/manual/1')).json();assert restarted==final
            await c.get('/api/v1/status');sessions=(await c.get('/api/v1/sessions/feeding')).json()
            assert len(sessions)==1 and sessions[0]['dispensed_grams']==meta['actual_dispensed_grams']
    asyncio.run(go())

@pytest.mark.parametrize('value,accepted',[(29,False),(30,True),(35,True),(36,True),(40,True),(41,False),(math.nextafter(40,math.inf),False),(math.nextafter(30,-math.inf),False),(float('nan'),False),(float('inf'),False),(True,False)])
def test_exact_mass_band_without_rounding(value,accepted):assert in_band(value) is accepted

def test_mock_journal_idempotent_conflict_busy_and_bounded(monkeypatch,tmp_path):
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','0');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','MOCK')
        app=make_app(tmp_path/'app.sqlite3');log=tmp_path/'journal.sqlite3'
        handles=d.mount(app,log,{'execution_context':'OFFLINE_TEST_ONLY'},system_provider=lambda:{},bridge_provider=lambda:{})
        note={'sensor_id':'SYNTHETIC','USER_OBSERVED':'TEST_ONLY','event_id':'OBS_1'}
        async with client(app) as c:
            assert (await c.post('/api/v1/hardware-diagnostics/observations',json=note)).status_code==200
            assert (await c.post('/api/v1/hardware-diagnostics/observations',json=note)).status_code==200
            assert len((await c.get('/api/v1/hardware-diagnostics/events')).json())==1
            assert (await c.post('/api/v1/hardware-diagnostics/observations',json={**note,'USER_OBSERVED':'CONFLICT'})).status_code==409
            lock=sqlite3.connect(log);lock.execute('BEGIN IMMEDIATE')
            try:assert (await c.post('/api/v1/hardware-diagnostics/observations',json={**note,'event_id':'OBS_2'})).status_code==503
            finally:lock.rollback();lock.close()
            for n in range(260):handles['journal'].add('SYNTHETIC',{'event_id':'BOUNDED_'+str(n)})
            export=(await c.get('/api/v1/hardware-diagnostics/events/export')).json();assert len(export['events'])==256 and export['physical_pass'] is False
    asyncio.run(go())

def test_atomic_rollback_terminal_once_busy_queue_and_timezone(monkeypatch,tmp_path):
    async def go():
        monkeypatch.setenv('ESP32_BRIDGE_ENABLED','0');monkeypatch.setenv('SYSTEM_STATE_PROVIDER','MOCK')
        path=tmp_path/'atomic.sqlite3';t=MockEsp32Transport();app=make_app(path,t,max_events=3)
        async with client(app) as c:
            ack=(await c.post('/api/v1/feed/manual')).json();t.complete_feed(ack['request_id'],FeedCode.SUCCESS)
            with closing(sqlite3.connect(path)) as db:
                with db:db.execute('CREATE TRIGGER synthetic_failure BEFORE INSERT ON events WHEN INSTR(NEW.body,\'"SUCCESS"\')>0 BEGIN SELECT RAISE(ABORT,\'SYNTHETIC_FAILURE\'); END')
            assert (await c.get('/api/v1/status')).status_code==503
            assert app.state.records.find_feed(request_id=1)[1]=='PENDING' and app.state.records.count('feeding')==0
            with closing(sqlite3.connect(path)) as db:
                with db:db.execute('DROP TRIGGER synthetic_failure')
            final=(await c.get('/api/v1/status')).json()['feeds'][0];assert final['state']=='SUCCESS' and final['actual_dispensed_grams'] is None
            app.state.feeds._set(1,app.state.feeds.feeds[1],final_received=True)
            assert app.state.records.count('feeding')==1
            assert sum(x.state=='SUCCESS' for x in app.state.store.list())==1
            assert all(x.timestamp.utcoffset().total_seconds()==0 for x in app.state.store.list())
            lock=sqlite3.connect(path);lock.execute('BEGIN IMMEDIATE');app.state.records.connection.execute('PRAGMA busy_timeout=80')
            before=len(t.feeds)
            try:assert (await c.post('/api/v1/feed/manual')).status_code==503
            finally:lock.rollback();lock.close()
            assert len(t.feeds)==before
        # Independent bounded pending queue; no camera or hardware simulation tick.
        q=make_app(tmp_path/'queue.sqlite3',MockEsp32Transport(),max_events=2)
        async with client(q) as c:
            assert (await c.post('/api/v1/feed/manual')).status_code==202
            assert (await c.post('/api/v1/feed/manual')).status_code==202
            assert (await c.post('/api/v1/feed/manual')).status_code==503
            assert len(q.state.transport.feeds)==2
    asyncio.run(go())

def test_request_id_first_writer_wins_across_connections(tmp_path):
    path=tmp_path/'claims.sqlite3';a=RecordRepository(path);b=RecordRepository(path);barrier=threading.Barrier(2)
    def claim(repo):barrier.wait(timeout=3);return repo.claim_feed('SYNTHETIC_SAME_KEY')
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,(a,b)))
        assert {x[0] for x in results}=={1} and sum(x[2] for x in results)==1
    finally:a.close();b.close()
