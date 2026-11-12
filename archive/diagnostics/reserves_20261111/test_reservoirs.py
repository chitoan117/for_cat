from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,sys,tempfile,time,unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
R=Path(__file__).parent
for name,filename in [('app.reservoir_levels','reservoir_levels.py'),('candidate_system_state','system_state.py'),('candidate_reservoir_routes','reservoir_routes.py')]:
    spec=importlib.util.spec_from_file_location(name,R/'backend'/filename);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
levels=sys.modules['app.reservoir_levels'];State=sys.modules['candidate_system_state'].RealHardwareProvider;routes=sys.modules['candidate_reservoir_routes']
from app.ultrasonic_state import unknown_channels
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'reservoir_calibration.json'
        self.path.write_text(json.dumps({'schema_version':1,'roles':{'food':{'empty_cm':14,'full_cm':None,'empty_tolerance_cm':.3},'water':{'empty_cm':20,'full_cm':None,'empty_tolerance_cm':.3}}}))
        self.channels=unknown_channels()
        for channel in self.channels.values():channel.update(wired=True,configured=True,enabled=True,valid=True,timeout=False,stale=False,state='HEALTHY',distance_cm=6.,sample_age_ms=0,last_update=100,last_valid_update=100,last_valid_distance_cm=6.,timeout_count=0)
        self.channels['HC_SR04_2']['distance_cm']=14.
        self.channels['JSN_SR04T_2']['distance_cm']=20.
        self.bridge={'telemetry_usable_now':True,'health':'ESP32_CONNECTED','last_rx_monotonic_ms':time.monotonic()*1000,'telemetry':{'ultrasonic':self.channels,'fc_live':{'pump_auto_enabled':False,'water_level_percent':97}}}
        self.provider=State(SimpleNamespace(status=lambda:self.bridge),reservoir_calibration_path=self.path)
    def tearDown(self):self.tmp.cleanup()
    def test_current_empty_is_zero_and_d1_never_becomes_food(self):
        for d1 in (3.,5.7,30.):
            self.channels['JSN_SR04T_1']['distance_cm']=d1
            for enabled in (False,True):
                self.bridge['telemetry']['fc_live']['pump_auto_enabled']=enabled
                result=self.provider.snapshot()
                self.assertEqual(result['food_reservoir_percent'],0)
                self.assertEqual(result['water_reservoir_percent'],0)
                self.assertEqual(result['reservoirs']['food']['sensor_label'],'E2')
                self.assertEqual(result['reservoirs']['water']['sensor_label'],'D2')
    def test_missing_full_does_not_invent_percent(self):
        self.channels['HC_SR04_2']['distance_cm']=8.
        v=self.provider.snapshot();self.assertIsNone(v['food_reservoir_percent']);self.assertEqual(v['reservoirs']['food']['state'],'NEEDS_FULL')
    def test_bad_config_hides_percent_without_losing_live_device(self):
        for content in ('[]','invalid json','{"schema_version":1,"roles":{"food":"bad"}}'):
            self.path.write_text(content)
            v=self.provider.snapshot();self.assertTrue(v['esp32']['connected']);self.assertIsNone(v['food_reservoir_percent'])
    def test_full_calibration_persists_and_interpolates(self):
        self.assertEqual(levels.save_full(self.path,'food',[4]*5),4)
        self.assertEqual(levels.save_full(self.path,'water',[5]*5),5)
        self.channels['HC_SR04_2']['distance_cm']=9.
        self.channels['JSN_SR04T_2']['distance_cm']=12.5
        v=self.provider.snapshot();self.assertEqual(v['food_reservoir_percent'],50);self.assertEqual(v['water_reservoir_percent'],50)
        self.channels['HC_SR04_2']['distance_cm']=4.
        self.assertEqual(self.provider.snapshot()['food_reservoir_percent'],100)
    def test_no_fallback_for_timeout_or_stale(self):
        ch=self.channels['HC_SR04_2'];ch.update(valid=False,distance_cm=None,state='TIMEOUT',timeout=True)
        self.assertIsNone(self.provider.snapshot()['food_reservoir_percent'])
        self.bridge['telemetry_usable_now']=False
        self.assertIsNone(self.provider.snapshot()['water_reservoir_percent'])
    def test_empty_cannot_be_saved_as_full_and_noisy_capture_rejected(self):
        for values in ([14]*5,[3,4,5,6,7]):
            with self.assertRaises(ValueError):levels.save_full(self.path,'food',values)
        self.assertIsNone(levels.load(self.path)['roles']['food']['full_cm'])
    def test_full_route_requires_confirmation_and_only_reads_selected_sensor(self):
        calls=0
        def snapshot():
            nonlocal calls
            calls+=1
            return {'data_source':'REAL','esp32':{'connected':True},'ultrasonic':{'HC_SR04_2':{'valid':True,'last_update':calls,'distance_cm':4.}}}
        app=FastAPI();app.state.store_path=self.path.with_name('events.db');app.state.system_state=SimpleNamespace(snapshot=snapshot);app.include_router(routes.router)
        with TestClient(app) as c:
            self.assertEqual(c.post('/api/reservoir-calibration',json={'role':'food','confirmed':False}).status_code,422)
            self.assertEqual(calls,0)
            self.assertEqual(c.post('/api/reservoir-calibration',json={'role':'food','confirmed':True}).status_code,200)
            self.assertEqual(levels.load(self.path)['roles']['food']['full_cm'],4)
            self.assertIsNone(levels.load(self.path)['roles']['water']['full_cm'])
if __name__=='__main__':unittest.main(verbosity=2)
