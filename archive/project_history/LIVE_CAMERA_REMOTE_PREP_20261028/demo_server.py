"""Loopback-only Windows synthetic video demo. No webcam/serial/model access."""
import argparse
from contextlib import asynccontextmanager
from datetime import datetime,timezone
import os
from pathlib import Path
import secrets
import sys
import uvicorn
import asyncio

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
from app.main import create_app
from app.config import HardwareConfig
from app.camera.live_stream import FrameHub,VideoSettings
from app.camera.remote_access import RemotePolicy
from synthetic_video import SyntheticProducer

def make_demo(web_dir=None,data_dir=None):
    folder=Path(data_dir) if data_dir else OUT/'demo_runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    # No feed worker/serial owner exists in this explicit synthetic camera demo.
    os.environ['ESP32_BRIDGE_ENABLED']='1';os.environ['SYSTEM_STATE_PROVIDER']='REAL';os.environ['SCHEDULED_DRY_RUN_WORKER_ENABLED']='0'
    hub=FrameHub(VideoSettings(enabled=True,source='SIMULATED',producer_token=secrets.token_urlsafe(32)))
    app=create_app(db_path=folder/'synthetic_camera.sqlite3',hardware=HardwareConfig(),live_camera=hub,
                   remote_policy=RemotePolicy(mode='LOCAL_DEMO'),flutter_web_dir=web_dir)
    producer=SyntheticProducer(hub)
    previous=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with previous(application):
            await producer.start()
            try:yield
            finally:await producer.stop()
    app.router.lifespan_context=lifespan
    app.state.synthetic_video=producer
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--web-dir')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('local demo port1024..65535')
    artifact=Path(args.web_dir) if args.web_dir else OUT/'web_real'
    app=make_demo(str(artifact) if artifact.is_dir() else None)
    print('SIMULATED VIDEO ONLY: http://127.0.0.1:%d/app | no hardware / production DB'%args.port)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,proxy_headers=False,timeout_graceful_shutdown=5))
    if sys.platform=='win32':
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:runner.run(server.serve())
    else:asyncio.run(server.serve())
