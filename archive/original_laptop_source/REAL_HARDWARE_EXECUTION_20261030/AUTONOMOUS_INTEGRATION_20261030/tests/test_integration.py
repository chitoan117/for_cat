import copy
import json
import os
from pathlib import Path
import struct
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.client import ClosedLoopClient
from backend.ledger import Ledger
from backend.replay import WorkerTransport
from backend.automation import AutoGate
from backend.api_patch import mount
from backend.wire import Command, Frame, encode, decode, FrameStreamDecoder, ProtocolError
from backend import contract

OUT = Path(os.environ['FORCAT_INTEGRATION_OUT'])
SETTINGS = (1450, 1550, 1500, 1550, 100, 40, 500, 12, 5., 5., .2, 35., 40.)
SAFETY = dict(weight_healthy=True, weight_fresh=True, calibration_valid=True, servo_reviewed=True,
              power_reviewed=True, journal_ready=True, calibration_id=7)


def ai(now, seq, species='CAT', **changes):
    value = dict(ai_schema_version=1, source='EXISTING_CPP_TENSORRT_OPTIONAL_FOOD_ROI', data_source='REAL',
                 simulated=False, actuator_execution=False, host_boot_id='HOST_TEST', producer_epoch='fixture-epoch',
                 health='ONLINE', source_frame_id=seq, roi_sequence=seq, roi_observation_ms=now,
                 updated_monotonic_ms=now, classification=species, confidence=.99 if species in ('CAT','DOG') else None,
                 roi_mode='ROI_ENABLED', roi_calibrated=True, roi_decision_eligible=True, frame_width=640, frame_height=480,
                 detections=[dict(species=species, bbox=dict(x1=.4,y1=.4,x2=.6,y2=.6))] if species in ('CAT','DOG') else [],
                 fixture_scope='SYNTHETIC_INPUT_RECORD_NOT_REAL_CAMERA_PROOF')
    value.update(changes);return value


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dir=OUT/'sandbox'/self._testMethodName;self.dir.mkdir(parents=True)
        self.ledger=Ledger(self.dir/'ledger.db')
        self.transport=WorkerTransport(OUT/'device_worker.exe', trace=self.dir/'wire_trace.jsonl')
        self.client=ClosedLoopClient(self.transport,self.ledger,authority=True)
        self.client.connect(1000);self.client.configure(SETTINGS,1010)

    def tearDown(self):
        self.transport.close();self.ledger.close()

    def receive_tick(self, now, **changes):
        for packet in self.transport.tick(now, **changes):self.client.receive(packet,now)

    def complete(self, request_id, start, mass=38, **changes):
        for delta in (100,200,300,400):
            self.receive_tick(start+delta, grams=100, closed=True, **changes)
            if delta==400:self.client.poll(start+delta)
        self.assertGreater(self.transport.last['opens'],0)
        self.receive_tick(start+500, grams=135, closed=False, **changes)
        for delta in range(600,2100,100):
            self.receive_tick(start+delta, grams=100+mass, closed=delta>=1000, **changes)
            if delta%400==0:self.client.poll(start+delta)
        return self.ledger.get(request_id)

    def test_connected_cat_protocol_controller_sql_api_fixture_38g(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','REVIEWED_FIXTURE_ROI')
        self.assertEqual(gate.observe(ai(1100,1),1100,SAFETY),'CONFIRMING_CAT')
        self.assertEqual(gate.observe(ai(1400,2),1400,SAFETY),'CONFIRMING_CAT')
        request_id=gate.observe(ai(1700,3),1700,SAFETY)
        self.assertIsInstance(request_id,int)
        ack=self.ledger.get(request_id)
        self.assertEqual(ack['state'],'PENDING');self.assertIsNone(ack['actual_dispensed_grams'])
        self.assertEqual(self.ledger.readonly('history'),[])
        final=self.complete(request_id,1700,38)
        self.assertEqual(final['state'],'COMPLETE');self.assertEqual(final['actual_dispensed_grams'],38)
        self.assertEqual(final['source'],'MOCK');self.assertTrue(final['closed']);self.assertTrue(final['journal_committed'])
        self.assertEqual(gate.observe(ai(3900,4),3900,SAFETY),'VISIT_ALREADY_CONSUMED')
        app=FastAPI();mount(app,self.ledger,lambda request,scope:request.headers.get('x-offline-view')=='fixture-only')
        with TestClient(app) as api:
            self.assertEqual(api.get('/api/v1/closed-loop/history').status_code,403)
            headers={'x-offline-view':'fixture-only'}
            response=api.get('/api/v1/closed-loop/history',headers=headers)
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['items'][0]['actual_dispensed_grams'],38)
            self.assertEqual(api.post('/api/v1/closed-loop/history',headers=headers).status_code,405)
            (OUT/'ui_fixtures/history.json').write_text(json.dumps(response.json(),indent=2))
            status=api.get('/api/v1/closed-loop/status',headers=headers).json()
            status['items']=[ack];(OUT/'ui_fixtures/pending.json').write_text(json.dumps(status,indent=2))

    def test_at_most_once_client_key_and_mcu_duplicate_request(self):
        request_id=self.client.request('once',1100)
        before=len(self.transport.sent)
        self.assertEqual(self.client.request('once',1150),request_id);self.assertEqual(before,len(self.transport.sent))
        self.complete(request_id,1100)
        opens=self.transport.last['opens']
        self.client.command(Command.FEED,3300,request_id=request_id)
        self.assertEqual(self.transport.last['opens'],opens)
        self.assertEqual(len(self.ledger.readonly('history')),1)

    def test_request_bound_progress_exposes_command_not_physical_position(self):
        request_id=self.client.request('progress',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.client.poll(1500)
        value=self.ledger.get(request_id)
        self.assertEqual(value['state'],'PENDING');self.assertEqual(value['servo_command_state'],'OPEN_COMMAND')
        self.assertIsNone(value['actual_dispensed_grams']);self.assertEqual(value['latest_observed_grams'],0)
        self.assertEqual(self.ledger.readonly('history'),[])
        app=FastAPI();mount(app,self.ledger,lambda request,scope:True)
        with TestClient(app) as api:
            data=api.get('/api/v1/closed-loop/status').json()
        (OUT/'ui_fixtures/progress.json').write_text(json.dumps(data,indent=2))

    def test_acceptance_30_and_40_and_35_target_not_cutoff30(self):
        request_id=self.client.request('edge30',1100)
        value=self.complete(request_id,1100,30)
        self.assertEqual(value['state'],'COMPLETE');self.assertEqual(value['actual_dispensed_grams'],30)

    def test_actual40_preserved(self):
        request_id=self.client.request('edge40',1100)
        value=self.complete(request_id,1100,40)
        self.assertEqual(value['state'],'COMPLETE');self.assertEqual(value['actual_dispensed_grams'],40)

    def test_persistent30_without_touching35_never_complete(self):
        request_id=self.client.request('not-at-aim',1100)
        for delta in range(100,5100,100):
            self.receive_tick(1100+delta,grams=100 if delta<=400 else 130,closed=True)
            if delta%400==0:self.client.poll(1100+delta)
        value=self.ledger.get(request_id)
        self.assertNotEqual(value['state'],'COMPLETE')

    def test_overshoot41_is_fault_not_coerced35(self):
        request_id=self.client.request('over',1100)
        value=self.complete(request_id,1100,41)
        self.assertEqual(value['state'],'FAULT');self.assertNotEqual(value['actual_dispensed_grams'],35)
        self.assertEqual(value['latest_observed_grams'],41)
        (OUT/'ui_fixtures/fault.json').write_text(json.dumps(dict(schema_version='forcat_closed_loop_view_v1',
            mass_policy=value['mass_policy'],execution_context='OFFLINE_SANDBOX',items=[value],actuator_execution=False),indent=2))

    def test_missing_closure_does_not_accept_settled38(self):
        request_id=self.client.request('close-unproven',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.receive_tick(1600,grams=135,closed=False)
        for delta in range(600,2100,100):
            self.receive_tick(1100+delta,grams=138,closed=False)
            if delta%400==0:self.client.poll(1100+delta)
        value=self.ledger.get(request_id)
        self.assertEqual(value['state'],'FAULT');self.assertEqual(value['reason'],104)
        self.assertTrue(self.transport.last['journal_pending']);self.assertFalse(value['closed'])

    def test_calibration_change_and_stale_scale_fail_closed(self):
        request_id=self.client.request('cal-change',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.receive_tick(1600,grams=135,calibration_id=8)
        self.receive_tick(2000,grams=135,calibration_id=8)
        value=self.ledger.get(request_id)
        self.assertEqual(value['state'],'FAULT');self.assertFalse(value['calibration_valid']);self.assertFalse(self.transport.last['pwm_attached'])

    def test_link_loss_timeout_closes_without_resend(self):
        request_id=self.client.request('lost',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.assertTrue(self.transport.last['pwm_attached'])
        self.client.disconnect()
        self.transport.tick(2700,grams=110);self.transport.tick(3100,grams=110)
        self.assertFalse(self.transport.last['pwm_attached']);self.assertEqual(self.ledger.get(request_id)['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(sum(x[7]==Command.FEED for x in self.transport.sent),1)

    def test_journal_failure_never_opens(self):
        self.transport.observation['journal_fail']=True
        with self.assertRaises(ValueError):self.client.request('journal-fail',1100)
        self.assertEqual(self.transport.last['opens'],0)
        self.assertEqual(self.ledger.readonly('history'),[])

    def test_restart_pending_locks_instead_of_resuming(self):
        request_id=self.client.request('reboot',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        opens=self.transport.last['opens'];self.client.disconnect();self.transport.reboot(1600)
        cap=self.client.connect(1700,124)
        self.assertTrue(cap['inspection_required'])
        with self.assertRaises(ValueError):self.client.request('new-after-boot',1800)
        self.assertEqual(self.transport.last['opens'],opens)
        self.assertEqual(self.ledger.get(request_id)['state'],'UNKNOWN_OUTCOME')

    def test_ack_loss_unknown_not_success_or_retransmit(self):
        self.transport.drop_ack=True
        with self.assertRaises(ValueError):self.client.request('ack-loss',1100)
        self.assertEqual(self.ledger.get(1)['state'],'UNKNOWN_OUTCOME')
        self.assertEqual(sum(x[7]==Command.FEED for x in self.transport.sent),0) # ARM ACK missing -> no FEED
        self.assertEqual(self.ledger.readonly('history'),[])

    def test_atomic_sql_rollback_then_query_recovery(self):
        request_id=self.client.request('atomic',1100)
        self.ledger.db.execute("CREATE TRIGGER fail_final BEFORE INSERT ON cl_events WHEN NEW.kind='FINAL_FEED_STATUS' BEGIN SELECT RAISE(FAIL,'injected'); END")
        self.ledger.db.commit()
        with self.assertRaises(Exception):self.complete(request_id,1100)
        self.assertEqual(self.ledger.readonly('history'),[]);self.assertEqual(self.ledger.get(request_id)['state'],'PENDING')
        self.ledger.db.execute('DROP TRIGGER fail_final');self.ledger.db.commit()
        self.client.command(Command.QUERY,self.client.last_now+1,request_id=request_id)
        self.assertEqual(self.ledger.get(request_id)['state'],'COMPLETE');self.assertEqual(len(self.ledger.readonly('history')),1)

    def test_dog_aborts_food_and_does_not_feed_each_frame(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','ROI_DOG_FIXTURE')
        for seq,now in enumerate((1100,1400,1700),1):request_id=gate.observe(ai(now,seq),now,SAFETY)
        for delta in (100,200,300,400):self.receive_tick(1700+delta,grams=100)
        gate.observe(ai(2200,4,'DOG'),2200,SAFETY)
        self.receive_tick(2600,grams=105)
        gate.observe(ai(2700,5,'DOG'),2700,SAFETY)
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT')
        self.assertEqual(self.transport.last['warning_starts'],1)
        self.assertEqual(sum(x[7]==Command.FEED for x in self.transport.sent),1)

    def test_ai_roi_legacy_stale_and_duplicate_frames_block(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','REVIEWED_ROI')
        self.assertEqual(gate.observe({'classification':'CAT'},1100,SAFETY),'BLOCKED_AI_METADATA_OR_STALE')
        self.assertEqual(gate.observe(ai(1200,1,roi_mode='FULL_FRAME'),1200,SAFETY),'BLOCKED_FOOD_ROI')
        gate.observe(ai(1300,2),1300,SAFETY)
        self.assertEqual(gate.observe(ai(1300,2),1400,SAFETY),'NO_NEW_AI_EVIDENCE')
        self.assertEqual(gate.observe(ai(100,3),2000,SAFETY),'BLOCKED_AI_METADATA_OR_STALE')
        self.assertEqual(self.ledger.readonly(),[])

    def test_visit_latch_survives_gate_restart(self):
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','ROI_PERSIST')
        for seq,now in enumerate((1100,1400,1700),1):request_id=gate.observe(ai(now,seq),now,SAFETY)
        self.complete(request_id,1700)
        gate=AutoGate(self.client,self.ledger,'HOST_TEST','ROI_PERSIST')
        self.assertEqual(gate.observe(ai(4000,10),4000,SAFETY),'VISIT_ALREADY_CONSUMED')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM cl_requests').fetchone()[0],1)

    def test_rejected_real_promotion_and_source_not_from_ai_label(self):
        with self.assertRaises(ValueError):self.ledger.claim('forged','REAL',1001,1,calibration=7)
        self.assertEqual(self.transport.source,'MOCK')

    def test_wire_crc_partial_and_legacy_manual_not_auto_capable(self):
        frame=Frame(1,Command.QUERY,contract.header(1001,1,1));data=encode(frame)
        stream=FrameStreamDecoder();self.assertEqual(stream.feed(data[:6],1),[])
        self.assertEqual(stream.feed(data[6:],1.01),[frame])
        bad=bytearray(data);bad[-1]^=1
        with self.assertRaises(ProtocolError):decode(bytes(bad))
        class Manual:
            source='MOCK'
            def exchange(self,*args):return [b'{"mode":"diag_manual_station"}\n']
        manual=ClosedLoopClient(Manual(),self.ledger,authority=True)
        with self.assertRaises(ValueError):manual.connect(1100)
        self.assertEqual(self.ledger.readonly(),[])

    def test_disabled_firmware_and_host_authority_block_before_request(self):
        other=WorkerTransport(OUT/'device_worker.exe',enabled=False)
        try:
            client=ClosedLoopClient(other,self.ledger,authority=True);client.connect(1100)
            with self.assertRaises(ValueError):client.request('disabled',1200)
            self.assertEqual(other.last['opens'],0);self.assertEqual(self.ledger.readonly(),[])
        finally:other.close()
        self.client.authority=False
        with self.assertRaises(ValueError):self.client.request('no-authority',1200)

    def test_final_payload_missing_proofs_never_complete(self):
        p=contract.RESULT.pack(1,1001,1,4,1,1,8,0,1,7,35,38,38)
        with self.assertRaises(ProtocolError):contract.result(Frame(1,Command.RESULT,p))
        p=contract.RESULT.pack(1,1001,1,4,1,1,8,0,127,7,35,41,41)
        with self.assertRaises(ProtocolError):contract.result(Frame(1,Command.RESULT,p))


if __name__=='__main__':unittest.main()
