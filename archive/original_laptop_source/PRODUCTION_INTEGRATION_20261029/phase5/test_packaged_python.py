"""Fresh subprocess proves imports/cache/API use the bundle, not root checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;RELEASE=HERE.parent/'release_candidate_v2'
def test_packaged_adapter_sqlite_api_import_and_provenance(tmp_path):
    code=r'''
import json,sys,sqlite3
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from app.ai_frame_contract import StateTap,PREFIX,SOURCE,WriterLock
from app.ai_state import AiStateReader
from app.main import create_app
from app.config import HardwareConfig
from app.camera.live_stream import FrameHub,VideoSettings
from app.camera.remote_access import RemotePolicy
import app.main as module
assert str(Path(module.__file__).resolve()).startswith(str(Path(sys.argv[1]).resolve()))
p=Path(sys.argv[2]);tap=StateTap(p,'boot',lambda:100)
data={'ai_schema_version':1,'data_source':'REAL','simulated':False,'actuator_execution':False,
'source':SOURCE,'host_boot_id':'boot','producer_epoch':'packaged','health':'ONLINE','classification':'DOG','confidence':.9,
'source_frame_id':1,'roi_sequence':1,'roi_observation_ms':100000,'updated_monotonic_ms':100000,
'roi_mode':'FULL_FRAME','roi_config_valid':True,'roi_calibrated':False,'bbox_available':True,
'roi_decision_eligible':True,'frame_width':640,'frame_height':480,'detections':[]}
with WriterLock(p):
    assert tap.accept(PREFIX+json.dumps(data))
    assert not tap.accept(PREFIX+json.dumps(data))
    assert not tap.accept(PREFIX+json.dumps({**data,'source_frame_id':2,'roi_sequence':2,'simulated':True}))
reader=AiStateReader(p,lambda:100,'boot')
assert reader.status()['classification']=='DOG' and reader.status()['producer_epoch']=='packaged'
assert AiStateReader(p,lambda:102,'boot').status()['health']=='STALE'
app=create_app(db_path=p,hardware=HardwareConfig(),live_camera=FrameHub(VideoSettings()),remote_policy=RemotePolicy(),scheduled_worker_enabled=False)
assert app.state.transport.feeds=={}
app.state.records.close();app.state.store.close()
with sqlite3.connect(p) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print(json.dumps({'packaged_pipeline':'PASS','simulation_only':True,'physical_pass':False,'camera_opened':False}))
'''
    env={**os.environ,'PYTHONPATH':str(RELEASE/'payload/jetson'),'PYTHONDONTWRITEBYTECODE':'1',
         'ESP32_BRIDGE_ENABLED':'1','SYSTEM_STATE_PROVIDER':'REAL','SCHEDULED_DRY_RUN_WORKER_ENABLED':'0'}
    p=subprocess.run([sys.executable,'-B','-c',code,str(RELEASE/'payload/jetson'),str(tmp_path/'local.sqlite3')],
                     cwd=tmp_path,env=env,capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stdout+p.stderr
    result=json.loads(p.stdout);assert result['physical_pass'] is False
