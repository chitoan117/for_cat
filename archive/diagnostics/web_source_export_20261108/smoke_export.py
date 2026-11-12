from pathlib import Path
import os,sys,tarfile,tempfile,json,hashlib

r=Path('/home/toan/for_cat/evidence/web_source_export_20261108')
snapshot=r/'smoke_snapshot';snapshot.mkdir(exist_ok=False)
with tarfile.open(r/'backend_release.tar.gz') as tar:
 for member in tar.getmembers():
  if not member.isfile():raise ValueError(member.name)
  p=(snapshot/member.name).resolve();assert p.is_relative_to(snapshot.resolve())
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
os.environ.update(ESP32_BRIDGE_ENABLED='0',SYSTEM_STATE_PROVIDER='MOCK',
                  SCHEDULED_DRY_RUN_WORKER_ENABLED='0',ESP32_TRANSPORT='MOCK',
                  CAMERA_PROVIDER='MOCK',AI_RUNTIME='MOCK')
sys.path.insert(0,str(snapshot/'backend/jetson'))
from app.main import create_app
from app.config import HardwareConfig
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory(dir=r) as td:
 db=str(Path(td)/'smoke.db')
 app=create_app(db_path=db,hardware=HardwareConfig(db_path=db),
                flutter_web_dir=snapshot/'web_release',scheduled_worker_enabled=False)
 checks={}
 with TestClient(app) as client:
  for path in ('/api/v1/health','/api/status','/api/meal-plans','/app','/flutter/main.dart.js'):
   response=client.get(path);assert response.status_code==200,(path,response.status_code)
   checks[path]=response.status_code
  assert client.get('/api/meal-plans').json()['plans']==[]
  assert client.get('/api/status').json()['data_source']=='MOCK'
  with client.websocket_connect('/api/ws/state') as ws:
   state=ws.receive_json();assert state['data_source']=='MOCK'
   checks['websocket /api/ws/state']='MOCK state received'
  assert hashlib.sha256(client.get('/flutter/main.dart.js').content).hexdigest()=='a7c6f3902bc30016068d1dabe90b87027208ab27d73369e23974e386351f9f5a'
 result={'isolated_export_app':True,'temporary_database':True,'serial_camera_mock':True,
         'scheduled_worker_enabled':False,'physical_commands_sent':False,'checks':checks}
(r/'smoke_result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
