import importlib.util,json,sqlite3,tempfile,time,unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
spec=importlib.util.spec_from_file_location('meal_routes',Path(__file__).parent/'backend/meal_observation_routes.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ApiTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.db=self.r/'events.db'
  m.CMD_FILE=self.r/'command.txt'
  with sqlite3.connect(self.db) as d:
   d.execute('CREATE TABLE esp32_latest(id INTEGER,body TEXT)')
   d.execute('CREATE TABLE esp32_events(seq INTEGER,occurred_at TEXT,kind TEXT,body TEXT)')
  self.live={'meal_schema_version':2,'meal_phase':'IDLE','bench_state':'READY','selected_food':'FOOD_A'}
  self.put_live()
  app=FastAPI();app.state.store_path=self.db;app.include_router(m.router);self.client=TestClient(app)
 def tearDown(self):self.client.close();self.tmp.cleanup()
 def put_live(self,stale=False):
  obj={'host_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'updated_monotonic_ms':time.monotonic()*1000-(10000 if stale else 0),'telemetry':{'fc_live':self.live}}
  with sqlite3.connect(self.db) as d:
   d.execute('DELETE FROM esp32_latest');d.execute('INSERT INTO esp32_latest VALUES(1,?)',(json.dumps(obj),))
 def test_select_only_and_busy_file(self):
  r=self.client.post('/api/meal-observation',json={'action':'SELECT_B'})
  self.assertEqual(r.status_code,202);self.assertFalse(r.json()['applied']);self.assertEqual(m.CMD_FILE.read_text(),'b\n')
  self.assertEqual(self.client.post('/api/meal-observation',json={'action':'SELECT_A'}).status_code,409)
  self.assertEqual(m.CMD_FILE.read_text(),'b\n')
  self.assertEqual(self.client.post('/api/meal-observation',json={'action':'pump_test'}).status_code,422)
 def test_finish_needs_real_stable_session(self):
  self.assertEqual(self.client.post('/api/meal-observation',json={'action':'FINISH'}).status_code,409)
  self.assertFalse(m.CMD_FILE.exists())
  self.live.update(meal_phase='OBSERVING',meal_stable=True,meal_elapsed_seconds=20);self.put_live()
  self.assertEqual(self.client.post('/api/meal-observation',json={'action':'FINISH'}).status_code,202)
  self.assertEqual(m.CMD_FILE.read_text(),'eval\n')
 def test_stale_never_queues(self):
  self.put_live(stale=True)
  self.assertEqual(self.client.post('/api/meal-observation',json={'action':'SELECT_A'}).status_code,503)
  self.assertFalse(m.CMD_FILE.exists())
 def test_final_history_is_persistent_measured_deduplicated(self):
  record={'schema_version':2,'final':True,'meal_id':'real_A','food':'FOOD_A','starting_g':35,'remaining_g':2,'consumed_g':33}
  for seq,body in [(1,record),(2,record),(3,{'food':'FOOD_A'}),(4,{**record,'meal_id':'fake','starting_g':None})]:
   with sqlite3.connect(self.db) as d:d.execute('INSERT INTO esp32_events VALUES(?,?,?,?)',(seq,'2026-11-10T00:00:00Z','meal_preference',json.dumps(body)))
  a=self.client.get('/api/meal-observation').json();b=self.client.get('/api/meal-observation').json()
  self.assertEqual(a['records'],b['records']);self.assertEqual(len(a['records']),1)
  self.assertEqual(a['records'][0]['id'],'real_A');self.assertEqual(a['records'][0]['consumed_g'],33)

if __name__=='__main__':unittest.main(verbosity=2)
