"""Actual loopback HTTP MJPEG clients + synthetic producer; no hardware access."""
import asyncio
import io
import json
from pathlib import Path
import socket
import sys
import time
import httpx
import uvicorn
from PIL import Image
from demo_server import make_demo

OUT=Path(__file__).resolve().parent
async def main():
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    app=make_demo(str(OUT/'web_real') if (OUT/'web_real').is_dir() else None)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,proxy_headers=False,log_level='error',timeout_graceful_shutdown=2))
    task=asyncio.create_task(server.serve(sockets=[sock]))
    result={'mode':'SIMULATED','physical_camera_opened':False,'network_scope':'LOOPBACK_ONLY','origin':'http://127.0.0.1:'+str(port)}
    def stage(name):
        result['stage']=name;(OUT/'http_progress.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(name,flush=True)
    try:
        while not server.started:await asyncio.sleep(.02)
        stage('server_started')
        async with httpx.AsyncClient(base_url=result['origin'],timeout=5) as client:
            await asyncio.sleep(.2);assert app.state.synthetic_video.encoded==0
            result['capture_continued_without_encode']=app.state.synthetic_video.captured>0
            await client.get('/api/v1/camera/status?watch=true')
            for _ in range(40):
                status=(await client.get('/api/v1/camera/status?watch=true')).json()
                if status['status']=='CAMERA_ONLINE':break
                await asyncio.sleep(.05)
            assert status['simulated'] is True
            stage('source_online')
            async with client.stream('GET','/api/v1/camera/mjpeg') as first,client.stream('GET','/api/v1/camera/mjpeg') as second:
                assert first.status_code==second.status_code==200
                active=(await client.get('/api/v1/camera/status')).json();assert active['viewers']==2
                stage('two_viewers')
                # A third client still shares a single latest-frame slot, not a
                # third producer/capture. Resource-budget behavior is tested too.
                app.state.live_camera.settings=type(app.state.live_camera.settings)(**{**app.state.live_camera.settings.__dict__,'max_viewers':2})
                assert (await client.get('/api/v1/camera/mjpeg?frames=1')).status_code==429
                stage('third_viewer_rejected')
                pending=bytearray();seen=[]
                async for chunk in first.aiter_bytes():
                    pending.extend(chunk)
                    while b'\r\n\r\n' in pending:
                        at=pending.find(b'\r\n\r\n');head=bytes(pending[:at]).decode('ascii');length=None;frame_id=None
                        for line in head.split('\r\n'):
                            if line.startswith('Content-Length: '):length=int(line.split(': ',1)[1])
                            if line.startswith('X-Frame-Id: '):frame_id=int(line.split(': ',1)[1])
                        if length is None or len(pending)<at+4+length+2:break
                        jpeg=bytes(pending[at+4:at+4+length]);del pending[:at+4+length+2]
                        image=Image.open(io.BytesIO(jpeg));image.load();assert image.size==(640,480)
                        red,green,blue=image.getpixel((630,10));assert red>80 and green<40 # visible SIMULATED banner
                        if not seen:(OUT/'simulated_http_frame.jpg').write_bytes(jpeg)
                        seen.append(frame_id)
                    if len(seen)>=3:break
                assert len(set(seen))>=3
                stage('three_frames_decoded')
                result['observed_frame_ids']=seen;result['two_http_viewers']='PASS';result['max_viewer_limit']='PASS'
            for _ in range(30):
                if not app.state.live_camera.viewers:break
                await asyncio.sleep(.03)
            assert not app.state.live_camera.viewers
            stage('viewers_released')
            result['disconnect_releases_viewers']=True
            assert app.state.transport.feeds=={}
            result['feed_side_effects']=False
            if (OUT/'web_real').is_dir():
                response=await client.get('/app');assert response.status_code==200 and '/flutter/' in response.text
                result['compiled_flutter_same_origin']='PASS'
        result['status']='PASS'
    finally:
        await app.state.live_camera.close();server.should_exit=True
        await asyncio.wait_for(task,10)
        (OUT/'windows_http_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    if sys.platform=='win32':
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:runner.run(main())
    else:asyncio.run(main())
