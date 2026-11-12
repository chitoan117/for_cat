"""API contract tests: local temp SQLite + synthetic JPEG; no physical devices."""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
sys.path.insert(0,str(ROOT/'LIVE_CAMERA_REMOTE_PREP_20261028'))
from test_ai_contract import frame, send, StateTap, AiStateReader
from synthetic_video import render_frame
from app.main import create_app
from app.config import HardwareConfig
from app.camera.live_stream import FrameHub, VideoSettings, MjpegResponse
from app.camera.remote_access import RemotePolicy

HOST='for-cat.tailtest.ts.net'
HEADERS={'x-forwarded-proto':'https','tailscale-user-login':'viewer@test'}
TOKEN='SYNTHETIC_PHASE4_ONLY_'+'x'*40

class Bridge:
    available=True
    def status(self):
        return {'telemetry_usable_now':self.available,'health':'ESP32_CONNECTED' if self.available else 'ESP32_STALE',
                'serial_connected':True,'host_boot_id':'boot','time_valid':False,
                'telemetry':{'monotonic_ms':1000,'mode':'TEST_FIXTURE','sensors':{
                    'hx711':{'raw_counts':-700000,'raw_available':True,'health':'NOT_CALIBRATED'},
                    'approach':{'distance_valid':True,'distance_cm':15,'health':'HEALTHY'}},
                    'safety':{'servo_armed':False,'pump_armed':False,'auto_feed':False,'auto_water':False,
                              'actuator_outputs_enabled':0,'actuator_execution':False}},
                'decisions':{'food_behavior':'IDLE','near_configured':True,'near_stable':True,'actuator_execution':False}}

@asynccontextmanager
async def api(tmp,monkeypatch):
    monkeypatch.setenv('ESP32_BRIDGE_ENABLED','1')
    monkeypatch.setenv('SYSTEM_STATE_PROVIDER','REAL')
    clock=[100.]
    hub=FrameHub(VideoSettings(enabled=True,source='REAL',producer_token=TOKEN),lambda:clock[0])
    policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname=HOST,users={
        'viewer@test':['VIEW_CAMERA'],'operator@test':['VIEW_CAMERA','FEED_MANUAL']})
    path=tmp/'api.sqlite3'
    app=create_app(db_path=path,hardware=HardwareConfig(),live_camera=hub,remote_policy=policy,
                   scheduled_worker_enabled=False)
    bridge=Bridge();app.state.esp32_reader=bridge
    provider=app.state.system_state.provider
    provider.reader=bridge;provider.ai_reader=AiStateReader(path,lambda:clock[0],'boot')
    provider.weight_calibration.clock=lambda:clock[0]
    tap=StateTap(path,'boot',lambda:clock[0])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1234)),base_url='https://'+HOST) as client:
            yield app,client,hub,tap,clock,bridge,path

@pytest.mark.parametrize('species',['CAT','DOG','NONE'])
def test_framed_stdout_sqlite_rest_and_camera_share_identity(tmp_path,monkeypatch,species):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            assert send(tap,frame(species=species))
            data,meta=render_frame(1,100000,species)
            meta.update(source='REAL',simulated=False,producer_epoch='producer_A')
            # Source flags represent the protocol fixture, never physical evidence.
            await hub.publish(data,meta)
            state=(await c.get('/api/status',headers=HEADERS)).json()
            ai=state['ai'];camera=(await c.get('/api/v1/camera/status',headers=HEADERS)).json()
            assert ai['classification']==camera['classification']==species
            assert ai['producer_epoch']==camera['producer_epoch']=='producer_A'
            assert ai['source_frame_id']==camera['frame_id']==1
            assert ai['captured_monotonic_ms']==100000 and ai['age_seconds']==0
            assert ai['data_source']=='REAL' and ai['simulated'] is False
            assert state['safety']['actuator_execution'] is False
            assert state['weight']['grams'] is None and state['decisions']['consumed_grams'] is None
            assert 'food_delta' not in state['weight'] # bowl tracker is not a live API module yet
            legacy=(await c.get('/api/v1/status',headers=HEADERS)).json()
            assert legacy['system_state']['ai']==ai
            stream=await c.get('/api/v1/camera/mjpeg?frames=1',headers=HEADERS)
            assert stream.status_code==200 and b'X-Frame-Id: 1' in stream.content and data in stream.content
            assert hub.status()['viewers']==0 and app.state.transport.feeds=={}
    asyncio.run(go())

def test_export_actual_api_fixture_for_flutter(tmp_path,monkeypatch):
    async def go():
        result={'kind':'SYNTHETIC_API_CONTRACT_NOT_PHYSICAL','physical_pass':False,'states':{},'camera':{}}
        async with api(tmp_path,monkeypatch) as (_,c,hub,tap,clock,bridge,path):
            for seq,species in enumerate(('CAT','DOG','NONE'),1):
                assert send(tap,frame(seq,species=species))
                result['states'][species]=(await c.get('/api/status',headers=HEADERS)).json()
            clock[0]=102
            result['states']['STALE']=(await c.get('/api/status',headers=HEADERS)).json()
            result['camera']['OFFLINE']=(await c.get('/api/v1/camera/status',headers=HEADERS)).json()
            for seq,source in enumerate(('REAL','SIMULATED'),1):
                # Independent fixture hubs, not two capture owners.
                h=FrameHub(replace(hub.settings,source=source),lambda:clock[0])
                data,meta=render_frame(seq,102000,'DOG');meta.update(source=source,simulated=source=='SIMULATED',producer_epoch='epoch_'+source)
                await h.publish(data,meta)
                result['camera'][source]=h.status();await h.close()
            posted=await c.post('/api/feed/preview',headers={**HEADERS,'tailscale-user-login':'operator@test'},
                                json={'request_id':'phase4_received','sub_source':'APP','target_grams':35})
            assert posted.status_code==202
            result['pending_receipt']=posted.json()
        out=HERE/'phase4';out.mkdir(exist_ok=True)
        (out/'api_contract_fixture.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    asyncio.run(go())

def test_ai_stale_or_simulated_cache_cannot_claim_real_or_authorize_feed(tmp_path,monkeypatch):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            assert send(tap,frame())
            clock[0]=102;bridge.available=False
            state=(await c.get('/api/status',headers=HEADERS)).json()
            assert state['ai']['classification']=='UNKNOWN' and state['ai']['health']=='STALE'
            assert state['decisions']['near_stable'] is False and state['weight']['grams'] is None
            assert tap.write({**frame(stamp=102000),'data_source':'SIMULATED','simulated':True})
            state=(await c.get('/api/status',headers=HEADERS)).json()
            assert state['ai']['classification']=='UNKNOWN'
            assert (await c.post('/api/v1/feed/manual',headers={**HEADERS,'tailscale-user-login':'operator@test'})).status_code==503
            assert app.state.transport.feeds=={}
    asyncio.run(go())

@pytest.mark.parametrize('change',[{}, {'origin':'https://evil.invalid'}, {'x-forwarded-proto':'http'},
    {'host':'evil.ts.net'},{'tailscale-user-login':'unknown@test'}])
def test_private_camera_and_control_permissions(tmp_path,monkeypatch,change):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            headers={**HEADERS,**change} if change else {}
            for endpoint in ('/api/status','/api/v1/camera/status','/api/v1/camera/mjpeg?frames=1'):
                assert (await c.get(endpoint,headers=headers)).status_code==403
            assert not hub.viewers and app.state.transport.feeds=={}
    asyncio.run(go())

def test_view_only_feed_scope_idempotent_received_and_history_contract(tmp_path,monkeypatch):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            body={'request_id':'phase4_one','sub_source':'APP','target_grams':35}
            assert (await c.post('/api/feed/preview',headers=HEADERS,json=body)).status_code==403
            op={**HEADERS,'tailscale-user-login':'operator@test'}
            first=await c.post('/api/feed/preview',headers=op,json=body)
            second=await c.post('/api/feed/preview',headers=op,json=body)
            assert first.status_code==second.status_code==202 and first.json()==second.json()
            receipt=(await c.get('/api/feed/preview/phase4_one',headers=op)).json()
            assert receipt['decision'] is None and receipt['request']['actual_dispensed_grams'] is None
            assert receipt['request']['actuator_execution'] is False
            assert (await c.post('/api/v1/feed/manual',headers=op)).status_code==503
            assert (await c.get('/api/v1/health',headers=HEADERS)).json()=={'status':'ok'}
            history=(await c.get('/api/v1/events',headers=HEADERS)).json()
            assert isinstance(history,list) and not any(e.get('kind')=='FEED_SUCCESS' for e in history)
            assert app.state.transport.feeds=={}
            with sqlite3.connect(path) as db:assert db.execute('SELECT COUNT(*) FROM feed_dry_run_requests').fetchone()[0]==1
    asyncio.run(go())

def test_lease_expiry_releases_viewer_and_new_stream_requires_permission(tmp_path,monkeypatch):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            data,meta=render_frame(1,100000);meta.update(source='REAL',simulated=False)
            await hub.publish(data,meta)
            response=MjpegResponse(hub,hub.acquire());messages=[]
            async def receive():await asyncio.Future()
            async def send_message(message):
                messages.append(message)
                if b'Content-Type: image/jpeg' in message.get('body',b''):clock[0]+=301
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send_message)
            assert not hub.viewers and any(b'--frame--' in m.get('body',b'') for m in messages)
            assert (await c.get('/api/v1/camera/mjpeg?frames=1')).status_code==403
            assert app.state.transport.feeds=={}
    asyncio.run(go())

def test_viewer_cap_and_private_producer_token_are_not_control_credentials(tmp_path,monkeypatch):
    async def go():
        async with api(tmp_path,monkeypatch) as (app,c,hub,tap,clock,bridge,path):
            data,meta=render_frame(1,100000);meta.update(source='REAL',simulated=False)
            await hub.publish(data,meta);viewers=[hub.acquire() for _ in range(4)]
            assert (await c.get('/api/v1/camera/mjpeg?frames=1',headers=HEADERS)).status_code==429
            for v in viewers:hub.release(v)
            assert (await c.get('/internal/camera/demand',headers=HEADERS)).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={'authorization':'Bearer '+TOKEN})).status_code==403
            assert (await c.post('/api/feed/preview',headers={'authorization':'Bearer '+TOKEN},json={})).status_code==403
            status=(await c.get('/api/v1/camera/status',headers=HEADERS)).text
            assert TOKEN not in status and 'producer_token' not in status
    asyncio.run(go())
