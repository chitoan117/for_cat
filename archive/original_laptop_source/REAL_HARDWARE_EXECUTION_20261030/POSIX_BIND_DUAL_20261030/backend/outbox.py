"""Backend -> SQLite outbox -> existing sole-owner C++ Bridge. No Serial API.
Windows integration uses an explicit drive callback for the actual source loop;
live capture remains NOT_AVAILABLE until separately qualified (never mislabeled MOCK).
"""
import json
from pathlib import Path
import sqlite3
import time
from .wire import Command, decode


class OutboxTransport:
    def __init__(self, path, producer, drive=None, timeout=2):
        self.path=Path(path).resolve();self.producer=producer;self.drive=drive;self.timeout=timeout
        self.cursor=0

    def _connect(self):
        return sqlite3.connect(self.path, timeout=.08)

    def state(self):
        with self._connect() as db:
            row=db.execute('SELECT body FROM cl_transport_state WHERE id=1').fetchone()
            return json.loads(row[0]) if row else {}

    @property
    def source(self):
        # This iteration validates the full owner loop with MOCK IO. A real
        # qualified capture adapter/writer is not fabricated by a configuration flag.
        state=self.state()
        return 'MOCK' if state.get('source')=='MOCK' else 'NOT_AVAILABLE'

    def exchange(self, packet, now):
        frame=decode(packet)
        with self._connect() as db:
            if db.execute("SELECT 1 FROM cl_transport_tx WHERE state='QUEUED'").fetchone():
                raise ConnectionError('another command is in flight')
            row=db.execute('INSERT INTO cl_transport_tx(producer,packet,state) VALUES(?,?,?)',
                           (self.producer,packet.hex(),'QUEUED'))
            queue_id=row.lastrowid
        deadline=time.monotonic()+self.timeout;packets=[]
        while time.monotonic()<deadline:
            if self.drive:self.drive(now)
            else:time.sleep(.01)
            with self._connect() as db:
                row=db.execute('SELECT state,error FROM cl_transport_tx WHERE seq=?',(queue_id,)).fetchone()
                incoming=db.execute('SELECT seq,packet,source FROM cl_transport_rx WHERE seq>? ORDER BY seq',(self.cursor,)).fetchall()
            if row[0] in ('BLOCKED','UNCERTAIN'):
                raise ConnectionError('Bridge '+row[0]+': '+str(row[1]))
            completed=False
            for seq,raw,source in incoming:
                self.cursor=seq
                if source!=self.source:raise ConnectionError('capture provenance mismatch')
                encoded=bytes.fromhex(raw);reply=decode(encoded);packets.append(encoded)
                if frame.command==Command.HELLO:
                    complete=reply.command==Command.CAPABILITIES and reply.request_id==frame.request_id
                elif frame.command==Command.QUERY:
                    complete=reply.command==Command.RESULT and reply.request_id==frame.request_id
                else:
                    complete=reply.command in (Command.ACK,Command.NACK) and reply.request_id==frame.request_id and len(reply.payload)==15 and reply.payload[13]==frame.command and reply.payload[9:13]==frame.payload[9:13]
                completed=completed or complete
            if completed:return packets
            state=self.state()
            if not state.get('connected') or not state.get('tx_reviewed'):
                raise ConnectionError('Bridge disconnected/review unavailable; no retry')
        # Never mark this row QUEUED again, even if the peer may have received it.
        raise TimeoutError('Bridge reply deadline; no automatic retransmission')

    def pending_rx(self, after):
        with self._connect() as db:
            return db.execute('SELECT seq,packet,source FROM cl_transport_rx WHERE seq>? ORDER BY seq',(after,)).fetchall()

    def collect(self):
        packets=[]
        for seq,raw,source in self.pending_rx(self.cursor):
            self.cursor=seq
            if source!=self.source:raise ConnectionError('capture provenance mismatch')
            packets.append(bytes.fromhex(raw))
        return packets
