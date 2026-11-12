from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,sqlite3,sys,tempfile,time,unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).parent
for name,file in [('app.water_control','water_control.py'),('candidate_water_routes','water_routes.py')]:
    spec=importlib.util.spec_from_file_location(name,ROOT/'backend'/file)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
m=sys.modules['app.water_control'];route=sys.modules['candidate_water_routes']
class Serial:
    def __init__(self):self.writes=[]
    def write(self,data):self.writes.append(data)
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'test.db'
        with sqlite3.connect(self.db) as db:db.execute('CREATE TABLE esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
        m.init(self.db);self.status={'pump_auto_enabled':False,'pump_auto_running':False,'pump_test_running':False,'pump_auto_fault':False,'bench_state':'READY'}
        self.store()
        app=FastAPI();app.state.store_path=self.db;app.include_router(route.router);self.client=TestClient(app)
        self.bridge=SimpleNamespace(db_path=self.db,boot_id=m.boot_id(),last_status=self.status,status_received_mono=time.monotonic())
        self.serial=Serial();self.dispatch=m.Dispatcher(self.bridge)
    def tearDown(self):self.client.close();self.tmp.cleanup()
    def store(self,stale=False):
        obj={'host_boot_id':m.boot_id(),'updated_monotonic_ms':time.monotonic()*1000-(10000 if stale else 0),'telemetry':{'fc_live':self.status,'ultrasonic':{'JSN_SR04T_1':{'distance_cm':6.2,'valid':True},'JSN_SR04T_2':{'distance_cm':15.0,'valid':True}}}}
        with sqlite3.connect(self.db) as db:db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)',(json.dumps(obj),))
    def post(self,action='ENABLE',ident='request1',confirmed=True):return self.client.post('/api/water-control',json={'request_id':ident,'action':action,'confirmed':confirmed})
    def req(self,ident='request1'):
        with sqlite3.connect(self.db) as db:return db.execute('SELECT status FROM water_requests WHERE id=?',(ident,)).fetchone()[0]
    def test_enable_needs_explicit_confirmation_and_fresh_device(self):
        self.assertEqual(self.post(confirmed=False).status_code,422)
        self.store(stale=True);self.assertEqual(self.post().status_code,503)
        self.assertEqual(self.serial.writes,[])
    def test_queued_is_not_enabled_until_fresh_ack(self):
        self.assertEqual(self.post().status_code,202)
        self.assertFalse(self.client.get('/api/water-control').json()['enabled'])
        self.dispatch.tick(self.serial);self.assertEqual(self.req(),'DISPATCHED')
        self.assertEqual(self.serial.writes,[b'pump_reset\npump_driver_verified\npump_auto on\n'])
        self.dispatch.tick(self.serial);self.assertEqual(len(self.serial.writes),1)
        self.status['pump_auto_enabled']=True;self.bridge.status_received_mono=time.monotonic();self.store()
        self.dispatch.tick(self.serial);self.assertEqual(self.req(),'APPLIED')
        self.assertTrue(self.client.get('/api/water-control').json()['enabled'])
    def test_duplicate_and_disable_preempt_enable(self):
        self.assertEqual(self.post().status_code,202);self.assertEqual(self.post().status_code,202)
        self.assertEqual(self.post('DISABLE','stop',False).status_code,202)
        self.assertEqual(self.req(),'CANCELLED');self.dispatch.tick(self.serial)
        self.assertEqual(self.serial.writes,[b'pump_auto off\npump_off\n'])
    def test_expired_enable_never_runs(self):
        self.post()
        with sqlite3.connect(self.db) as db:db.execute('UPDATE water_requests SET requested=requested-20')
        self.dispatch.tick(self.serial);self.assertEqual(self.req(),'EXPIRED');self.assertEqual(self.serial.writes,[])
    def test_restart_cancels_prior_enable_and_only_stops(self):
        self.post();self.dispatch.on_connect(self.serial);self.assertEqual(self.req(),'CANCELLED')
        self.assertEqual(self.serial.writes,[b'pump_auto off\npump_off\n'])
        self.post(ident='after_reconnect');m.startup_off(self.db)
        self.assertEqual(self.req('after_reconnect'),'CANCELLED')
        self.dispatch.tick(self.serial);self.assertTrue(all(b'pump_auto on' not in x for x in self.serial.writes))
    def test_timeout_stops_and_does_not_claim_enabled(self):
        self.post();self.dispatch.tick(self.serial)
        with sqlite3.connect(self.db) as db:db.execute('UPDATE water_requests SET dispatched=dispatched-5')
        self.dispatch.tick(self.serial);self.assertEqual(self.req(),'TIMEOUT')
        self.assertEqual(self.serial.writes[-1],b'pump_auto off\npump_off\n')
    def test_malformed_action_rejected_and_stop_allowed_when_stale(self):
        self.assertEqual(self.client.post('/api/water-control',json={'request_id':'bad','action':'pump_test'}).status_code,422)
        self.store(stale=True);self.assertEqual(self.post('DISABLE','safe_stop',False).status_code,202)
    def test_busy_device_cannot_enable(self):
        self.status['bench_state']='CAT OPENING';self.store();self.assertEqual(self.post().status_code,409)
    def test_esp32_reboot_does_not_replay_enable(self):
        self.status['boot']=100;self.dispatch.tick(self.serial)
        self.post();self.status['boot']=101
        self.dispatch.tick(self.serial);self.assertEqual(self.req(),'CANCELLED')
        self.assertEqual(self.serial.writes,[b'pump_auto off\npump_off\n'])
if __name__=='__main__':unittest.main(verbosity=2)
