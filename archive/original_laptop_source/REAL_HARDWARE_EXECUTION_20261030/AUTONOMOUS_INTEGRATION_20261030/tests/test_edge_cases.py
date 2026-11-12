import unittest
from tests import test_integration as common
from backend.wire import Command, Frame, encode, decode
from backend import contract


class EdgeTests(unittest.TestCase):
    setUp=common.IntegrationTests.setUp
    tearDown=common.IntegrationTests.tearDown
    receive_tick=common.IntegrationTests.receive_tick
    complete=common.IntegrationTests.complete

    def test_feed_ack_lost_but_final_authoritative_no_retry(self):
        self.transport.drop_ack_for=Command.FEED
        with self.assertRaises(ValueError):self.client.request('lost-feed-ack',1100)
        self.assertEqual(self.ledger.get(1)['state'],'UNKNOWN_OUTCOME')
        self.complete(1,1100,38)
        self.assertEqual(self.ledger.get(1)['state'],'UNKNOWN_OUTCOME')
        self.client.connect(3300,124)
        self.client.command(Command.QUERY,3301,request_id=1)
        final=self.ledger.get(1)
        self.assertTrue(final['final_status_received']);self.assertTrue(final['reconciled_from_unknown'])
        self.assertEqual(sum(x[7]==Command.FEED for x in self.transport.sent),1)

    def test_crc_and_fragmented_requests_use_actual_mcu_parser(self):
        heartbeat=encode(Frame(0,Command.HEARTBEAT,contract.header(self.client.cap['boot'],self.client.cap['session'],2)))
        self.assertEqual(self.transport.exchange(heartbeat[:8],1100),[])
        replies=self.transport.exchange(heartbeat[8:],1110)
        self.assertEqual(decode(replies[0]).command,Command.ACK)
        self.client.seq=2
        bad=bytearray(encode(Frame(1,Command.FEED,contract.header(self.client.cap['boot'],self.client.cap['session'],3))))
        bad[-1]^=1
        self.assertEqual(self.transport.exchange(bad,1120),[])
        self.assertEqual(self.transport.last['opens'],0);self.assertEqual(self.transport.last['journal_last'],0)

    def test_transport_fault_before_pending_pulse_never_opens(self):
        request_id=self.client.request('cancel-before-pulse',1100)
        for delta in (100,200,300):self.receive_tick(1100+delta,grams=100)
        self.receive_tick(1500,grams=100,transport_fault=True)
        self.receive_tick(1900,grams=100,transport_fault=False)
        self.assertEqual(self.transport.last['opens'],0)
        self.assertFalse(self.transport.last['pwm_attached'])
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT')

    def test_stale_scale_after_open_closes_fault(self):
        request_id=self.client.request('stale-scale',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.receive_tick(1800,grams=110,fresh=False,sample_at=0)
        self.receive_tick(2200,grams=110,fresh=False,sample_at=0)
        self.assertFalse(self.transport.last['pwm_attached'])
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT')

    def test_wrong_session_aborts_active_request(self):
        request_id=self.client.request('wrong-session',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        bad=encode(Frame(0,Command.HEARTBEAT,contract.header(self.client.cap['boot'],999,self.client.seq+1)))
        self.transport.exchange(bad,1600)
        self.receive_tick(2000,grams=110)
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT');self.assertFalse(self.transport.last['pwm_attached'])

    def test_dog_cooldown_never_suppresses_abort(self):
        gate=common.AutoGate(self.client,self.ledger,'HOST_TEST','DOG_COOLDOWN_EDGE')
        gate.observe(common.ai(1100,1,'DOG'),1100,common.SAFETY)
        for seq,now in enumerate((1300,1600,1900),2):request_id=gate.observe(common.ai(now,seq),now,common.SAFETY)
        for delta in (100,200,300,400):self.receive_tick(1900+delta,grams=100)
        self.assertEqual(gate.observe(common.ai(2400,5,'DOG'),2400,common.SAFETY),'DOG_NO_FEED_COOLDOWN')
        self.receive_tick(2800,grams=105)
        self.assertEqual(self.ledger.get(request_id)['state'],'FAULT')
        self.assertEqual(self.transport.last['warning_starts'],1)

    def test_failed_dog_transport_stops_heartbeat_until_safe_timeout(self):
        request_id=self.client.request('dog-unconfirmed',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        original=self.transport.exchange
        def failure(data,now):
            if data[7]==Command.DOG:raise ConnectionError('injected before write')
            return original(data,now)
        self.transport.exchange=failure
        with self.assertRaises(ConnectionError):self.client.dog(1600)
        self.assertIsNone(self.client.cap)
        sent=len(self.transport.sent);self.client.poll(1800);self.assertEqual(len(self.transport.sent),sent)
        self.transport.tick(2700,grams=110);self.transport.tick(3100,grams=110)
        self.assertFalse(self.transport.last['pwm_attached'])
        self.assertEqual(self.ledger.get(request_id)['state'],'UNKNOWN_OUTCOME')

    def test_failed_heartbeat_cannot_keep_refreshing_mcu_lease(self):
        request_id=self.client.request('heartbeat-unconfirmed',1100)
        for delta in (100,200,300,400):self.receive_tick(1100+delta,grams=100)
        self.transport.drop_ack=True
        with self.assertRaises(ValueError):self.client.poll(1800)
        self.assertIsNone(self.client.cap)
        sent=len(self.transport.sent);self.client.poll(2000);self.assertEqual(len(self.transport.sent),sent)
        self.transport.tick(3400,grams=110);self.transport.tick(3800,grams=110)
        self.assertFalse(self.transport.last['pwm_attached'])
        self.assertEqual(self.ledger.get(request_id)['state'],'UNKNOWN_OUTCOME')


if __name__=='__main__':unittest.main()
