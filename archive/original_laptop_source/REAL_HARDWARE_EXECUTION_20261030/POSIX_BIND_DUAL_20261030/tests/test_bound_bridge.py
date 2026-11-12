import json
import os
from pathlib import Path
import sqlite3
import subprocess
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.client import ClosedLoopClient
from backend.ledger import Ledger
from backend.outbox import OutboxTransport
from backend.automation import AutoGate
from backend.api_patch import mount
from backend.wire import Command, Frame, encode
from backend import contract
from tests.bridge_driver import BridgeDriver

OUT=Path(os.environ['FORCAT_BOUND_OUT'])
SETTINGS=(1450,1550,1500,1550,100,40,500,12,5.,5.,.2,35.,40.)
SAFETY=dict(weight_healthy=True,weight_fresh=True,calibration_valid=True,servo_reviewed=True,power_reviewed=True,journal_ready=True,calibration_id=7)


def ai(now,seq,species='CAT'):
    return dict(ai_schema_version=1,source='EXISTING_CPP_TENSORRT_OPTIONAL_FOOD_ROI',data_source='REAL',simulated=False,
        actuator_execution=False,host_boot_id='HOST_TEST',producer_epoch='SIMULATED_RECORD_ONLY',health='ONLINE',source_frame_id=seq,
        roi_sequence=seq,roi_observation_ms=now,updated_monotonic_ms=now,classification=species,confidence=.99 if species!='NONE' else None,
        roi_mode='ROI_ENABLED',roi_calibrated=True,roi_decision_eligible=True,frame_width=640,frame_height=480,
        detections=[] if species=='NONE' else [dict(species=species,bbox=dict(x1=.4,y1=.4,x2=.6,y2=.6))])


class BoundBridgeTests(unittest.TestCase):
    def setUp(self):
        self.dir=OUT/'sandbox'/self._testMethodName;self.dir.mkdir(parents=True)
        self.ledger=Ledger(self.dir/'ledger.db')
        dual=self._testMethodName.startswith('test_dual_')
        self.driver=BridgeDriver(OUT/'actual_bridge_test.exe',self.dir,self.ledger,enabled=not dual,dual=dual)
        self.transport=OutboxTransport(self.ledger.path,'offline-automation',self.driver.drive)
        self.client=ClosedLoopClient(self.transport,self.ledger,authority=True)
        self.client.connect(1000)
        if not dual:self.client.configure(SETTINGS,1010)

    def tearDown(self):
        self.driver.close();self.ledger.close()

    def step(self,now,**changes):
        self.driver.drive(now,**changes);self.driver.drive(now)
        for packet in self.transport.collect():self.client.receive(packet,now)

    def finish(self,request_id,start,closed=True):
        for delta in (100,200,300,400):self.step(start+delta,grams=100)
        self.assertGreater(self.driver.last['opens'],0)
        self.step(start+500,grams=135,closed=False)
        for delta in range(600,2100,100):
            self.step(start+delta,grams=138,closed=closed and delta>=1000)
            if delta%400==0:self.client.poll(start+delta)
        return self.ledger.get(request_id)

    def test_automation_actual_posix_source_outbox_device_final_sql_api(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','ROI_BOUND_SOURCE')
        for seq,now in enumerate((1100,1400,1700),1):request_id=gate.observe(ai(now,seq),now,SAFETY)
        self.assertEqual(self.ledger.get(request_id)['state'],'PENDING')
        self.assertEqual(self.ledger.readonly('history'),[])
        final=self.finish(request_id,1700)
        self.assertEqual(final['state'],'COMPLETE');self.assertEqual(final['actual_dispensed_grams'],38)
        self.assertEqual(final['source'],'MOCK');self.assertEqual(self.driver.last['owner_opens'],1)
        self.assertEqual(self.driver.last['bridge_source'],'esp32_bridge.cpp::bridge')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM cl_wire_consumed').fetchone()[0],1)
        self.assertEqual(self.ledger.db.execute("SELECT COUNT(*) FROM cl_transport_tx WHERE state='TX_DONE'").fetchone()[0]>0,True)
        app=FastAPI();mount(app,self.ledger,lambda request,scope:True)
        with TestClient(app) as api:
            value=api.get('/api/v1/closed-loop/history').json()
        self.assertEqual(value['items'][0]['actual_dispensed_grams'],38)
        (self.dir/'api_history.json').write_text(json.dumps(value,indent=2))
        with sqlite3.connect(self.dir/'bridge.db') as db:
            status=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        self.assertTrue(status['feed_link_bound_in_bridge']);self.assertEqual(status['source'],'MOCK')
        self.assertEqual(gate.observe(ai(3900,4),3900,SAFETY),'VISIT_ALREADY_CONSUMED')

    def test_same_request_cannot_retransmit_through_durable_bridge_store(self):
        request_id=self.client.request('once-bound',1100);self.finish(request_id,1100)
        opens=self.driver.last['opens']
        with self.assertRaises(ConnectionError):self.client.command(Command.FEED,3300,request_id=request_id)
        self.assertEqual(self.driver.last['opens'],opens)
        row=self.ledger.db.execute('SELECT state FROM cl_transport_tx ORDER BY seq DESC LIMIT 1').fetchone()[0]
        self.assertEqual(row,'BLOCKED');self.assertEqual(len(self.ledger.readonly('history')),1)

    def test_no_physical_closure_not_success_even_when_mass38(self):
        request_id=self.client.request('closure-unproven',1100)
        result=self.finish(request_id,1100,closed=False)
        self.assertEqual(result['state'],'FAULT');self.assertFalse(result['closed'])
        self.assertEqual(result['actual_dispensed_grams'],38);self.assertTrue(result['mass_in_band'])
        self.assertTrue(self.driver.last['journal_pending'])

    def test_cable_loss_releases_owner_and_unknown_no_repeat(self):
        request_id=self.client.request('cable',1100)
        for delta in (100,200,300,400):self.step(1100+delta,grams=100)
        self.driver.drive(1600,connected=False,grams=110)
        with self.assertRaises(ConnectionError):self.client.poll(1700)
        self.driver.drive(2800,connected=False);self.driver.drive(3200,connected=False)
        self.assertFalse(self.driver.last['pwm_attached'])
        self.assertEqual(self.ledger.get(request_id)['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM cl_wire_consumed').fetchone()[0],1)
        with sqlite3.connect(self.dir/'bridge.db') as db:
            status=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        self.assertFalse(status['serial_tx_enabled']);self.assertFalse(status['feed_tx_enabled'])

    def test_wrong_producer_and_crc_rejected_before_writer(self):
        packet=encode(Frame(0,Command.HEARTBEAT,contract.header(self.client.cap['boot'],self.client.cap['session'],self.client.seq+1)))
        with self.ledger.db:
            self.ledger.db.execute("INSERT INTO cl_transport_tx(producer,packet,state) VALUES(?,?,'QUEUED')",('not-approved',packet.hex()))
        self.driver.drive(1100)
        self.assertEqual(self.ledger.db.execute('SELECT state FROM cl_transport_tx ORDER BY seq DESC LIMIT 1').fetchone()[0],'BLOCKED')
        bad=bytearray(packet);bad[-1]^=1
        with self.ledger.db:self.ledger.db.execute("INSERT INTO cl_transport_tx(producer,packet,state) VALUES(?,?,'QUEUED')",('offline-automation',bad.hex()))
        self.driver.drive(1200)
        self.assertEqual(self.ledger.db.execute('SELECT state FROM cl_transport_tx ORDER BY seq DESC LIMIT 1').fetchone()[0],'BLOCKED')
        self.assertEqual(self.driver.last['opens'],0)

    def test_real_source_database_lock_prevents_second_bridge_owner(self):
        q=subprocess.run(self.driver.command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertEqual(q.returncode,1);self.assertIn(b'another canonical bridge',q.stderr)
        self.assertEqual(self.driver.last['owner_opens'],1)

    def test_default_plan_never_constructs_loop_or_opens_port(self):
        q=subprocess.run([str(OUT/'actual_bridge_test.exe'),'--default-plan'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertEqual(q.returncode,0);self.assertFalse(json.loads(q.stdout)['serial_opened'])

    def test_queued_old_sequence_never_becomes_new_arm(self):
        stale=encode(Frame(0,Command.ARM,contract.header(self.client.cap['boot'],self.client.cap['session'],1)))
        with self.ledger.db:self.ledger.db.execute("INSERT INTO cl_transport_tx(producer,packet,state) VALUES(?,?,'QUEUED')",('offline-automation',stale.hex()))
        self.driver.drive(1100)
        self.assertEqual(self.ledger.db.execute('SELECT state FROM cl_transport_tx ORDER BY seq DESC LIMIT 1').fetchone()[0],'BLOCKED')
        self.assertFalse(self.driver.last['pwm_attached'])

    def test_partial_write_consumes_id_and_never_requeues(self):
        def drive(now):
            row=self.ledger.db.execute("SELECT packet FROM cl_transport_tx WHERE state='QUEUED' ORDER BY seq LIMIT 1").fetchone()
            partial=bool(row and bytes.fromhex(row[0])[7]==Command.FEED)
            return self.driver.drive(now,short_write=partial)
        self.transport.drive=drive
        with self.assertRaises(ConnectionError):self.client.request('partial-bound',1100)
        self.assertEqual(self.ledger.get(1)['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(self.ledger.db.execute('SELECT state FROM cl_transport_tx ORDER BY seq DESC LIMIT 1').fetchone()[0],'UNCERTAIN')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM cl_wire_consumed').fetchone()[0],1)
        self.driver.drive(2700,grams=110);self.driver.drive(3100,grams=110)
        self.assertFalse(self.driver.last['pwm_attached']);self.assertEqual(self.driver.last['opens'],0)

    def test_dual_stream_mux_json_and_binary_are_separate_inert_domains(self):
        self.assertFalse(self.client.cap['enabled']);self.assertFalse(self.client.cap['closure_available'])
        with self.assertRaises(ValueError):self.client.configure(SETTINGS,1010)
        report=(Path(__file__).resolve().parents[1]/'dual_tests/boot.json').read_text()
        self.driver.drive(1100,ascii=report)
        for _ in range(6):self.driver.drive(1100)
        with sqlite3.connect(self.dir/'bridge.db') as db:
            value=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        self.assertEqual(value['telemetry']['wire_mode'],'diag_dual_station')
        self.assertFalse(value['telemetry']['closed_loop_feed_capability'])
        self.assertFalse(value['feed_tx_enabled']);self.assertFalse(value['actuator_execution'])
        self.assertEqual(self.driver.last['owner_opens'],1);self.assertEqual(self.driver.last['opens'],0)

    def test_dual_unsafe_json_also_disconnects_bound_control_transport(self):
        value=json.loads((Path(__file__).resolve().parents[1]/'dual_tests/boot.json').read_text())
        value['current_hardware']['auto_feed']=True
        self.driver.drive(1100,ascii=json.dumps(value)+'\n')
        for _ in range(6):self.driver.drive(1100)
        self.assertFalse(self.transport.state()['connected'])
        with sqlite3.connect(self.dir/'bridge.db') as db:
            status=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        self.assertFalse(status['serial_connected']);self.assertTrue(status['unsafe_telemetry_latched'])
        self.assertFalse(status['serial_tx_enabled'])

    def test_stale_peer_cannot_be_published_as_feed_ready(self):
        self.driver.drive(3000)
        with sqlite3.connect(self.dir/'bridge.db') as db:
            value=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
        self.assertEqual(value['health'],'ESP32_STALE');self.assertFalse(value['feed_tx_enabled'])
        self.assertFalse(value['actuator_execution'])

    def test_sql_error_during_disconnect_cannot_keep_heartbeats_alive(self):
        self.client.request('db-fault-disconnect',1100)
        for delta in (100,200,300,400):self.step(1100+delta,grams=100)
        self.ledger.db.execute("CREATE TRIGGER fail_unknown BEFORE INSERT ON cl_events WHEN NEW.kind='UNKNOWN_OUTCOME_NO_RESEND' BEGIN SELECT RAISE(FAIL,'injected'); END")
        self.ledger.db.commit()
        with self.assertRaises(sqlite3.Error):self.client.disconnect('injected')
        self.assertIsNone(self.client.cap)
        before=self.ledger.db.execute('SELECT COUNT(*) FROM cl_transport_tx').fetchone()[0]
        self.client.poll(1800)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM cl_transport_tx').fetchone()[0],before)
        self.driver.drive(2700,grams=110);self.driver.drive(3100,grams=110)
        self.assertFalse(self.driver.last['pwm_attached']);self.assertEqual(self.ledger.readonly('history'),[])

    def test_dog_abort_goes_through_bridge_source_not_callback_only(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','ROI_BOUND_DOG')
        for seq,now in enumerate((1100,1400,1700),1):request_id=gate.observe(ai(now,seq),now,SAFETY)
        for delta in (100,200,300,400):self.step(1700+delta,grams=100)
        gate.observe(ai(2200,4,'DOG'),2200,SAFETY);self.step(2600,grams=105)
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT');self.assertEqual(self.driver.last['warning_starts'],1)


if __name__=='__main__':unittest.main()
