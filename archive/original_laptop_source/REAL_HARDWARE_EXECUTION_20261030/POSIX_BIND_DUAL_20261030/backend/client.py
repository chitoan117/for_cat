"""Conditional byte transport client. No Serial/socket API or automatic FEED retry."""
import struct
import secrets
from . import contract
from .wire import Command, Frame, encode, FrameStreamDecoder, ProtocolError


class ClosedLoopClient:
    def __init__(self, transport, ledger, *, authority=False):
        self.transport, self.ledger = transport, ledger
        if transport.source != 'MOCK':
            raise ValueError('live sole-owner Bridge adapter still requires hardware qualification')
        self.authority = authority
        self.decoder = FrameStreamDecoder()
        self.cap = None
        self.seq = 0
        self.last_now = 0
        self.active_id = None
        self.sent_at = 0
        self.rejected_packets = 0
        self.expected_hello = None
        self.awaiting = None
        self.last_ack = None

    def receive(self, chunk, now):
        if now < self.last_now:
            self.disconnect('HOST_CLOCK_REGRESSION'); raise ValueError('host clock regressed')
        self.last_now = now
        for frame in self.decoder.feed(chunk, now / 1000):
            if frame.command == Command.CAPABILITIES:
                if self.expected_hello is None or frame.request_id != self.expected_hello:
                    self.rejected_packets += 1; continue
                self.cap = contract.capabilities(frame)
                self.expected_hello = None
                continue
            if not self.cap:
                self.rejected_packets += 1; continue
            if frame.command in (Command.ACK, Command.NACK):
                if len(frame.payload) != 15:
                    self.rejected_packets += 1; continue
                schema, boot, session, seq = contract.HEADER.unpack(frame.payload[:13])
                if (schema, boot, session) != (1, self.cap['boot'], self.cap['session']) or seq > self.seq:
                    self.rejected_packets += 1; continue
                op, reason = frame.payload[13:]
                if self.awaiting != (seq, op, frame.request_id):
                    self.rejected_packets += 1; continue
                self.last_ack = (frame.command, reason)
                if op == Command.FEED and frame.request_id == self.active_id:
                    if frame.command == Command.ACK:
                        self.ledger.pending(frame.request_id)
                    else:
                        self.ledger.reject(frame.request_id, reason)
                continue
            if frame.command == Command.RESULT:
                value = contract.result(frame)
                if (value['boot'], value['session']) != (self.cap['boot'], self.cap['session']) or value['sequence'] > self.seq:
                    self.rejected_packets += 1; continue
                if value['final_status_received']:
                    self.ledger.finish(value)
                    if value['request_id'] == self.active_id:
                        self.active_id = None
                else:
                    self.ledger.progress(value)

    def _exchange(self, frame, now):
        replies = self.transport.exchange(encode(frame), now)
        for chunk in replies:
            self.receive(chunk, now)
        return replies

    def connect(self, now, client_nonce=None):
        self.cap = None; self.seq = 0; self.decoder = FrameStreamDecoder()
        client_nonce = client_nonce or secrets.randbits(31) or 1
        self.expected_hello = client_nonce
        self._exchange(Frame(client_nonce, Command.HELLO, struct.pack('<BI', 1, client_nonce)), now)
        if not self.cap:
            raise ValueError('BLOCKED_FIRMWARE: explicit closed-loop handshake absent; manual mode is not compatible')
        return self.cap

    def command(self, operation, now, payload=b'', request_id=0):
        if not self.cap:
            raise ValueError('no validated link')
        self.seq += 1
        h = contract.header(self.cap['boot'], self.cap['session'], self.seq)
        self.awaiting = (self.seq, int(operation), request_id); self.last_ack = None
        replies = self._exchange(Frame(request_id, operation, h + payload), now)
        if operation != Command.QUERY and (not self.last_ack or self.last_ack[0] != Command.ACK):
            if self.active_id is not None and operation == Command.ARM and self.last_ack:
                self.ledger.reject(self.active_id, self.last_ack[1])
            raise ValueError('ACK_TIMEOUT_OR_NACK: no automatic retry')
        return replies

    def configure(self, values, now):
        if not self.authority or not self.cap or not self.cap['enabled'] or not self.cap['closure_available'] or not self.cap['ready']:
            raise ValueError('BLOCKED_GATES: actuation/journal/closure authority absent')
        self.command(Command.CONFIGURE, now, contract.configuration(values))
        self.cap['configured'] = True

    def request(self, key, now):
        if not self.authority or not self.cap or not self.cap['enabled'] or not self.cap['closure_available'] or not self.cap['ready'] or not self.cap['configured']:
            raise ValueError('BLOCKED_GATES')
        # Durable reserve happens before any FEED bytes. Existing key never resends.
        request_id, fresh = self.ledger.claim(key, self.transport.source, self.cap['boot'], self.cap['session'], self.cap['last_id'], self.cap['calibration_id'])
        if not fresh:
            return request_id
        self.active_id, self.sent_at = request_id, now
        try:
            self.command(Command.ARM, now)
            self.command(Command.FEED, now, request_id=request_id)
        except Exception:
            self.disconnect('TRANSPORT_OR_STORE_FAILURE_NO_RESEND')
            raise
        return request_id

    def poll(self, now):
        try:
            if self.active_id is not None and now - self.sent_at > 65000:
                self.ledger.unknown(self.active_id, 'HOST_DEADLINE_NO_RESEND')
                self.command(Command.ABORT, now, request_id=self.active_id)
            elif self.cap:
                self.command(Command.HEARTBEAT, now)
                if self.active_id is not None:
                    self.command(Command.QUERY, now, request_id=self.active_id)
        except Exception:
            self.disconnect('HEARTBEAT_OR_ABORT_UNCONFIRMED')
            raise

    def disconnect(self, reason='DISCONNECTED'):
        self.cap = None
        self.decoder = FrameStreamDecoder()
        if self.active_id is not None:
            self.ledger.unknown(self.active_id, reason)

    def dog(self, now):
        if self.cap and self.authority:
            try:
                self.command(Command.DOG, now, request_id=self.active_id or 0)
            except Exception:
                self.disconnect('DOG_ABORT_UNCONFIRMED')
                raise
