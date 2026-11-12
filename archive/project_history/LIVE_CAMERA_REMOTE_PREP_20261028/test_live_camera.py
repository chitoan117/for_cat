import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import replace
import json
from pathlib import Path
import sys
import time

import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
from app.main import create_app
from app.config import HardwareConfig
from app.camera.live_stream import FrameHub,VideoSettings,MjpegResponse,validate_meta,jpeg_dimensions
from app.camera.remote_access import RemotePolicy
from starlette.requests import ClientDisconnect
from synthetic_video import render_frame,SyntheticProducer

TOKEN='OFFLINE_TEST_ONLY_'+'a'*40
def settings(**kw):return VideoSettings(enabled=True,source='SIMULATED',producer_token=TOKEN,**kw)
@asynccontextmanager
async def api(tmp,policy=None,client=('127.0.0.1',1234),base='http://localhost',hub=None):
    tmp.mkdir(parents=True,exist_ok=True)
    hub=hub or FrameHub(settings())
    app=create_app(db_path=tmp/'test.sqlite3',hardware=HardwareConfig(),live_camera=hub,
                   remote_policy=policy or RemotePolicy(mode='LOCAL_DEMO'))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=client),base_url=base) as browser:
            yield app,hub,browser

def test_mjpeg_boundary_and_release(tmp_path):
    async def go():
        async with api(tmp_path) as (_,hub,c):
            data,meta=render_frame(1,int(hub.clock()*1000));await hub.publish(data,meta)
            response=await c.get('/api/v1/camera/mjpeg?frames=1')
            assert response.status_code==200 and response.headers['content-type'].startswith('multipart/x-mixed-replace; boundary=frame')
            assert b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' in response.content
            assert data in response.content and response.content.endswith(b'--frame--\r\n')
            assert response.headers['x-camera-source']=='SIMULATED' and hub.status()['viewers']==0
    asyncio.run(go())

def test_offline_reconnect_and_epoch():
    async def go():
        now=[100.0];hub=FrameHub(settings(),monotonic=lambda:now[0])
        assert hub.status()['status']=='CAMERA_OFFLINE'
        data,meta=render_frame(1,100000);await hub.publish(data,meta)
        assert hub.status()['status']=='CAMERA_ONLINE'
        now[0]=103;assert hub.status()['status']=='CAMERA_OFFLINE' and hub.status()['buffered_bytes']==0
        data,meta=render_frame(1,103000);meta['producer_epoch']='RECONNECTED';await hub.publish(data,meta)
        assert hub.status()['status']=='CAMERA_ONLINE'
        await hub.close();assert hub.status()['status']=='CAMERA_OFFLINE'
    asyncio.run(go())

def test_bounded_viewers_latest_drop_slow_client():
    async def go():
        now=[100.0];hub=FrameHub(settings(max_viewers=2),monotonic=lambda:now[0])
        data,meta=render_frame(1,100000);await hub.publish(data,meta)
        first,second=hub.acquire(),hub.acquire()
        with pytest.raises(Exception) as error:hub.acquire()
        assert error.value.status_code==429
        for n in range(2,80):
            data,meta=render_frame(n,100000);await hub.publish(data,meta)
        frame=await hub.next_frame(1)
        assert frame[1]['frame_id']==79 and hub.status()['frame_slots']==1
        assert hub.status()['buffered_bytes']<=hub.settings.max_jpeg_bytes and hub.dropped==78
        hub.release(first);hub.release(second);assert not hub.viewers
    asyncio.run(go())

@pytest.mark.parametrize('mutation',[
    {'metadata_frame_id':0},{'overlay_frame_id':True},{'width':320},{'height':0},
    {'metadata_monotonic_ms':99999},{'captured_monotonic_ms':1,'metadata_monotonic_ms':1},
    {'classification':'OWNER_CAT'},{'confidence':float('nan')},{'simulated':False},
    {'detections':[{'species':'CAT','bbox':[0,0,2,1]}]},
    {'food_roi':[0,0,1,1]}, {'overlay_applied':False},
    {'roi_mode':'ROI_ENABLED','food_roi':None},
])
def test_metadata_not_stale_or_wrong_frame(mutation):
    data,meta=render_frame(1,100000);meta.update(mutation)
    with pytest.raises(ValueError):validate_meta(meta,data,settings(),100000)

def test_jpeg_and_source_contract():
    data,meta=render_frame(1,100000,'DOG',True)
    assert jpeg_dimensions(data)==(640,480)
    assert validate_meta(meta,data,settings(),100000)['food_roi'] is not None
    with pytest.raises(ValueError):validate_meta(meta,data,replace(settings(),source='REAL'),100000)
    with pytest.raises(ValueError):validate_meta(meta,b'not a JPEG',settings(),100000)
    for species in ('CAT','DOG','NONE'):
        jpeg,m=render_frame(2,100000,species,False)
        assert validate_meta(m,jpeg,settings(),100000)['classification']==species and m['food_roi'] is None

def test_disconnect_and_send_timeout_release():
    async def go():
        hub=FrameHub(settings(send_timeout_seconds=.01));data,meta=render_frame(1,int(hub.clock()*1000));await hub.publish(data,meta)
        response=MjpegResponse(hub,hub.acquire())
        async def receive():return {'type':'http.disconnect'}
        async def send(_):await asyncio.sleep(.1)
        try:await response({'type':'http','asgi':{'spec_version':'2.3'}},receive,send)
        except (Exception,BaseExceptionGroup):pass
        assert hub.status()['viewers']==0
    asyncio.run(go())

def test_real_send_timeout_without_disconnect_releases_viewer():
    async def go():
        hub=FrameHub(settings(send_timeout_seconds=.01));data,meta=render_frame(1,int(hub.clock()*1000));await hub.publish(data,meta)
        response=MjpegResponse(hub,hub.acquire())
        async def receive():await asyncio.sleep(1);return {'type':'http.request'}
        async def slow_send(_):await asyncio.sleep(.1)
        with pytest.raises((asyncio.TimeoutError,ClientDisconnect)):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,slow_send)
        assert not hub.viewers
    asyncio.run(go())

def test_producer_private_no_identity_header_bypass(tmp_path):
    async def go():
        async with api(tmp_path) as (_,hub,c):
            data,meta=render_frame(1,int(hub.clock()*1000))
            headers={'x-frame-meta':base64.b64encode(json.dumps(meta).encode()).decode()}
            assert (await c.post('/internal/camera/frame',content=data,headers=headers)).status_code==403
            headers['authorization']='Bearer '+TOKEN
            assert (await c.post('/internal/camera/frame',content=data,headers={**headers,'tailscale-user-login':'viewer@test'})).status_code==403
            assert (await c.post('/internal/camera/frame',content=data,headers=headers)).status_code==200
            assert (await c.get('/internal/camera/demand',headers={'authorization':'Bearer '+TOKEN})).json()['viewers']==0
            await c.get('/api/v1/camera/status?watch=true')
            assert (await c.get('/internal/camera/demand',headers={'authorization':'Bearer '+TOKEN})).json()['viewers']==1
    asyncio.run(go())

def test_tailscale_scopes_and_remote_spoof_rejected(tmp_path):
    async def go():
        policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='for-cat.example.ts.net',users={'viewer@test':['VIEW_CAMERA'],'operator@test':['VIEW_CAMERA','FEED_MANUAL']})
        headers={'x-forwarded-proto':'https','tailscale-user-login':'viewer@test'}
        async with api(tmp_path/'trusted',policy,base='https://for-cat.example.ts.net') as (_,hub,c):
            assert (await c.get('/api/v1/camera/status')).status_code==403
            assert (await c.get('/api/v1/camera/status',headers=headers)).status_code==200
            assert (await c.post('/api/v1/feed/manual',headers=headers)).status_code==403
            assert (await c.post('/api/feed/preview',headers=headers)).status_code==403
            assert (await c.post('/api/v1/meal-plans',headers=headers)).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={**headers,'origin':'https://evil.invalid'})).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={**headers,'tailscale-user-login':'stranger@test'})).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={**headers,'x-forwarded-proto':'http'})).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={**headers,'host':'other.example.ts.net'})).status_code==403
            assert (await c.get('/api/v1/camera/status',headers={**headers,'host':'for-cat.example.ts.net:bad'})).status_code==403
            assert (await c.post('/api/feed/preview',headers={**headers,'tailscale-user-login':'operator@test'},json={'request_id':'camera_permission_check','sub_source':'APP','target_grams':35})).status_code==503
        async with api(tmp_path/'untrusted',policy,client=('100.66.1.2',4444),base='https://for-cat.example.ts.net') as (_,_,c):
            assert (await c.get('/api/v1/camera/status',headers=headers)).status_code==403
        async with api(tmp_path/'disabled',RemotePolicy(),hub=FrameHub(VideoSettings())) as (_,_,c):
            assert (await c.get('/api/v1/camera/status')).status_code==403
            assert (await c.post('/api/v1/feed/manual',headers=headers)).status_code==403
    asyncio.run(go())

def test_viewing_has_no_feed_transport_or_request_side_effects(tmp_path):
    async def go():
        async with api(tmp_path) as (app,hub,c):
            data,meta=render_frame(1,int(hub.clock()*1000));await hub.publish(data,meta)
            before=dict(app.state.transport.feeds)
            await c.get('/api/v1/camera/status?watch=true');await c.get('/api/v1/camera/mjpeg?frames=1')
            assert app.state.transport.feeds==before=={}
            assert app.state.scheduled_worker.enabled is False
    asyncio.run(go())

def test_python_usb_capture_cannot_join_shared_cpp_owner(tmp_path):
    with pytest.raises(ValueError,match=r'C\+\+ owns webcam'):
        create_app(db_path=tmp_path/'never_opened.db',hardware=HardwareConfig(camera_provider='USB',camera_device='/dev/video0'),
                   live_camera=FrameHub(settings()),remote_policy=RemotePolicy(mode='LOCAL_DEMO'))

def test_injected_usb_capture_is_also_rejected_without_open(tmp_path):
    from app.camera.usb_webcam import UsbWebcamCameraProvider
    bare=object.__new__(UsbWebcamCameraProvider) # no constructor/camera call
    with pytest.raises(ValueError,match=r'C\+\+ owns webcam'):
        create_app(db_path=tmp_path/'never_opened.db',hardware=HardwareConfig(),camera=bare,
                   live_camera=FrameHub(settings()),remote_policy=RemotePolicy(mode='LOCAL_DEMO'))

def test_websocket_uses_same_tailnet_permission_boundary():
    from app.camera.remote_access import CameraAccessMiddleware
    async def go():
        called=[];messages=[]
        async def target(scope,receive,send):called.append(True)
        async def receive():return {'type':'websocket.connect'}
        async def send(message):messages.append(message)
        policy=RemotePolicy(mode='TAILSCALE_SERVE',hostname='for-cat.example.ts.net',users={'viewer@test':['VIEW_CAMERA']})
        guard=CameraAccessMiddleware(target,policy)
        scope={'type':'websocket','path':'/api/ws/state','client':('127.0.0.1',1),'headers':[(b'host',b'for-cat.example.ts.net'),(b'x-forwarded-proto',b'https')]}
        await guard(scope,receive,send);assert not called and messages[-1]['code']==4403
        await guard({**scope,'headers':scope['headers']+[(b'tailscale-user-login',b'viewer@test')]},receive,send);assert called==[True]
    asyncio.run(go())

def test_no_viewers_no_encode_ai_continues():
    async def go():
        hub=FrameHub(settings());producer=SyntheticProducer(hub,fps=20);await producer.start()
        try:
            await asyncio.sleep(.12);assert producer.captured>0 and producer.encoded==0
            hub.request_preview();await asyncio.sleep(.12);assert producer.encoded>0
            hub.preview_until=0;before=producer.encoded;captured=producer.captured
            await asyncio.sleep(.12);assert producer.encoded==before and producer.captured>captured
        finally:await producer.stop();await hub.close()
    asyncio.run(go())

def test_remote_config_requires_loopback_and_explicit_allowlist(tmp_path):
    policy=tmp_path/'access.json';token=tmp_path/'token'
    policy.write_text(json.dumps({'users':{'viewer@test':['VIEW_CAMERA'],'operator@test':['VIEW_CAMERA','FEED_MANUAL']}}))
    token.write_text('a'*48)
    env={'FORCAT_REMOTE_MODE':'TAILSCALE_SERVE','API_HOST':'127.0.0.1','FORCAT_TAILSCALE_HOSTNAME':'for-cat.example.ts.net',
         'FORCAT_ACCESS_POLICY_FILE':str(policy),'FORCAT_STREAM_ENABLED':'1','FORCAT_CAMERA_PRODUCER_TOKEN_FILE':str(token)}
    assert RemotePolicy.from_env(env).users['viewer@test']==['VIEW_CAMERA']
    assert VideoSettings.from_env(env).source=='REAL'
    for bad in ({'API_HOST':'0.0.0.0'},{'CORS_ORIGINS':'*'},{'FORCAT_ACCESS_POLICY_FILE':str(tmp_path/'missing')}):
        with pytest.raises(ValueError):RemotePolicy.from_env({**env,**bad})
