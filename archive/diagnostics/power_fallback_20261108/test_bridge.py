from pathlib import Path
from contextlib import closing
import importlib.util,sys,types,tempfile,sqlite3,json,unittest
r=Path(__file__).parent
sys.modules['serial']=types.SimpleNamespace(Serial=object)
spec=importlib.util.spec_from_file_location('bridge_candidate',r/'fc_live_bridge.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class UART:
 def __init__(self):self.commands=[]
 def write(self,data):self.commands.append(data.decode().strip())
 def flush(self):pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=r);root=Path(self.tmp.name)
  self.now=1000.;m.time=types.SimpleNamespace(time=lambda:self.now,monotonic=lambda:self.now)
  m.CMD_FILE=root/'cmd';m.FOOD_MODE_FILE=root/'food';self.b=m.BridgeRunner(root/'test.db');self.u=UART()
  self.b.last_status={'bench_state':'READY','signed_g':0,'scheduled_protocol':1,'demo_exited':False,'inspect_required':False,'dog_running':False};self.b.status_received_mono=self.now
  self.sql('CREATE TABLE feed_dry_run_requests(request_id TEXT PRIMARY KEY,body TEXT,decision TEXT)')
  self.sql('CREATE TABLE scheduled_occurrences(request_id TEXT PRIMARY KEY,due_unix_ms INTEGER)')
  self.sql('CREATE TABLE ai_latest(id INTEGER PRIMARY KEY,body TEXT)')
  self.b.clock.probe=lambda:True
 def tearDown(self):self.tmp.cleanup()
 def sql(self,sql,args=()):
  with closing(sqlite3.connect(self.b.db_path,isolation_level=None)) as db:return db.execute(sql,args).fetchall()
 def request(self,name='schedule_one'):
  body={'request_id':name,'source':'SCHEDULED','target_grams':35,'actuator_execution':False,'actual_dispensed_grams':None}
  self.sql('INSERT INTO feed_dry_run_requests VALUES(?,?,NULL)',(name,json.dumps(body)));self.sql('INSERT INTO scheduled_occurrences VALUES(?,?)',(name,int(self.now*1000)))
 def decision(self,name='schedule_one'):
  value=self.sql('SELECT decision FROM feed_dry_run_requests WHERE request_id=?',(name,))[0][0];return json.loads(value) if value else None
 def tick(self):self.b.status_received_mono=self.now;self.b.scheduled_delivery.tick(self.u)
 def ack(self,status):self.b.scheduled_delivery.handle({'type':'scheduled_ack','request_id':'schedule_one','status':status,'reason':status})
 def ai(self,label,conf,now):
  self.now=now;self.b.status_received_mono=now
  body={'classification':label,'confidence':conf,'updated_monotonic_ms':now*1000,'host_boot_id':self.b.boot_id,'health':'ONLINE'}
  self.sql('INSERT OR REPLACE INTO ai_latest VALUES(1,?)',(json.dumps(body),));self.b.check_commands_and_ai(self.u)
 def test_ack_retry_busy_and_restart(self):
  self.request();self.b.last_status['bench_state']='WAIT 35g';self.tick();self.assertEqual(self.u.commands,[])
  self.b.last_status['bench_state']='READY';self.tick();self.assertEqual(self.u.commands,['feed_once schedule_one']);self.assertIsNone(self.decision())
  self.now+=.5;self.tick();self.assertEqual(len(self.u.commands),1)
  self.now+=1.1;self.tick();self.assertEqual(self.u.commands,['feed_once schedule_one']*2)
  self.ack('BUSY');self.assertIsNone(self.decision());self.now+=1.6;self.tick();self.assertEqual(len(self.u.commands),3)
  self.ack('ACCEPTED');self.assertEqual(self.decision()['delivery_state'],'ACKNOWLEDGED')
  restarted=m.BridgeRunner(self.b.db_path);self.assertEqual(self.decision()['delivery_state'],'ACKNOWLEDGED')
  self.now+=2;self.tick();self.assertEqual(len(self.u.commands),3)
  self.b.scheduled_delivery.handle({'type':'scheduled_result','request_id':'schedule_one','status':'WEIGHT_REACHED','measured_at_close_g':35.4})
  self.ack('DUPLICATE');self.assertEqual(self.decision()['delivery_state'],'WEIGHT_REACHED');self.assertIsNone(self.decision()['actual_dispensed_grams'])
 def test_expiry_protocol_stale_and_inspection(self):
  self.request();self.b.last_status['scheduled_protocol']=0;self.tick();self.assertFalse(self.u.commands)
  self.b.last_status['scheduled_protocol']=1;self.b.status_received_mono=0;self.b.scheduled_delivery.tick(self.u);self.assertFalse(self.u.commands)
  self.b.last_status['inspect_required']=True;self.tick();self.assertEqual(self.decision()['delivery_state'],'REJECTED')
  self.request('schedule_expired');self.now+=61;self.tick();self.assertEqual(self.decision('schedule_expired')['delivery_state'],'EXPIRED');self.assertFalse(self.u.commands)
 def test_oled_dog_is_independent_of_actuator_confirmation(self):
  self.b.last_status['bench_state']='CAT OPENING'
  self.ai('DOG',.5,1000);self.assertIn('ai_dog',self.u.commands);self.assertNotIn('2',self.u.commands)
  self.ai('NONE',0,1000.1);self.assertEqual(self.u.commands[-1],'ai_none')
  for t in (1001,1001.5,1002.1):self.ai('DOG',.9,t)
  self.assertIn('2',self.u.commands)
 def test_cat_and_manual_transport_remain(self):
  self.ai('CAT',.9,1000);self.ai('CAT',.9,1000.2);self.assertIn('1',self.u.commands)
  m.CMD_FILE.write_text('weight\n');self.ai('NONE',0,1001);self.assertIn('weight',self.u.commands)
 def test_accepted_attempt_without_result_is_not_replayed(self):
  self.request();self.tick();self.ack('ACCEPTED');self.now+=61;self.tick()
  self.assertEqual(self.decision()['delivery_state'],'UNCERTAIN');self.assertEqual(self.u.commands,['feed_once schedule_one'])
 def test_pending_survives_restart_before_first_send(self):
  self.request();self.b=m.BridgeRunner(self.b.db_path)
  self.b.clock.probe=lambda:True
  self.assertIsNone(self.decision())
  self.b.last_status={'bench_state':'READY','scheduled_protocol':1,'demo_exited':False,'inspect_required':False,'dog_running':False}
  self.tick();self.assertEqual(self.u.commands,['feed_once schedule_one'])
 def test_sent_without_ack_survives_restart_and_retries_same_id(self):
  self.request();self.tick();self.now+=2
  self.b=m.BridgeRunner(self.b.db_path);self.assertIsNone(self.decision())
  self.b.clock.probe=lambda:True
  self.b.last_status={'bench_state':'READY','scheduled_protocol':1,'demo_exited':False,'inspect_required':False,'dog_running':False}
  self.tick();self.assertEqual(self.u.commands,['feed_once schedule_one']*2)
  self.ack('DUPLICATE');self.assertEqual(self.decision()['delivery_state'],'ACKNOWLEDGED')
 def test_pending_restart_after_window_expires_without_uart(self):
  self.request();self.now+=61;self.b=m.BridgeRunner(self.b.db_path)
  self.b.clock.probe=lambda:True
  self.tick();self.assertEqual(self.decision()['delivery_state'],'EXPIRED');self.assertFalse(self.u.commands)
 def test_unverified_boot_clock_never_sends_then_verified_clock_can_send(self):
  self.request();self.b.clock.probe=lambda:False;self.tick();self.assertFalse(self.u.commands)
  self.assertIsNone(self.decision())
  self.now+=5;self.b.clock.probe=lambda:True;self.tick();self.assertEqual(self.u.commands,['feed_once schedule_one'])
 def test_host_heartbeat_independent_of_missing_ai(self):
  self.b.check_commands_and_ai(self.u);self.assertEqual(self.u.commands,['jetson_ping'])
  self.now+=1;self.b.check_commands_and_ai(self.u);self.assertEqual(len(self.u.commands),1)
  self.now+=.6;self.b.check_commands_and_ai(self.u);self.assertEqual(self.u.commands,['jetson_ping']*2)
if __name__=='__main__':unittest.main()
