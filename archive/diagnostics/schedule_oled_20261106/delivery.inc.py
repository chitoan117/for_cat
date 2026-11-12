class ScheduledDelivery:
    """Durable, bounded delivery of one scheduled attempt, acknowledged by MCU."""
    def __init__(self, bridge):
        self.bridge = bridge
        with closing(sqlite3.connect(bridge.db_path)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS scheduled_delivery(request_id TEXT PRIMARY KEY,'
                       'state TEXT NOT NULL,reason TEXT,attempts INTEGER NOT NULL DEFAULT 0,last_sent REAL NOT NULL DEFAULT 0)')
            db.commit()

    def finish(self, db, identifier, body, state, reason, **extra):
        decision = make_canonical_decision(identifier, body,
            'DISPATCHED_TO_ESP32_35G' if state == 'ACKNOWLEDGED' else 'SCHEDULED_'+reason)
        data = json.loads(decision)
        data.update(delivery_state=state, delivery_reason=reason, **extra)
        db.execute('UPDATE feed_dry_run_requests SET decision=? WHERE request_id=?', (json.dumps(data), identifier))
        db.execute('UPDATE scheduled_delivery SET state=?,reason=? WHERE request_id=?', (state, reason, identifier))

    def handle(self, msg):
        identifier=msg.get('request_id')
        with closing(sqlite3.connect(self.bridge.db_path,timeout=1)) as db:
            row=db.execute('SELECT r.body,d.state FROM feed_dry_run_requests r JOIN scheduled_delivery d USING(request_id) WHERE request_id=?',(identifier,)).fetchone()
            if not row or json.loads(row[0]).get('source')!='SCHEDULED': return
            if msg.get('type')=='scheduled_result':
                state='WEIGHT_REACHED' if msg.get('status')=='WEIGHT_REACHED' else 'FAILED'
                self.finish(db,identifier,row[0],state,state,measured_at_close_g=msg.get('measured_at_close_g'))
            elif msg.get('status') in ('ACCEPTED','DUPLICATE'):
                # A late duplicate acknowledgement cannot overwrite a completed result.
                if row[1] not in ('WEIGHT_REACHED','FAILED'):
                    self.finish(db,identifier,row[0],'ACKNOWLEDGED',msg.get('reason','ACCEPTED'))
            elif msg.get('status')=='BUSY':
                db.execute('UPDATE scheduled_delivery SET state=?,reason=? WHERE request_id=?',('QUEUED',msg.get('reason'),identifier))
            elif msg.get('status')=='REJECTED':
                self.finish(db,identifier,row[0],'REJECTED',msg.get('reason','REJECTED'))
            db.commit()

    def tick(self, ser):
        now=time.time()
        with closing(sqlite3.connect(self.bridge.db_path,timeout=.5)) as db:
            missing=db.execute("SELECT r.request_id,r.body FROM scheduled_delivery d JOIN feed_dry_run_requests r USING(request_id) WHERE d.state='ACKNOWLEDGED' AND d.last_sent<?",(now-60,)).fetchall()
            for identifier,body in missing:
                self.finish(db,identifier,body,'UNCERTAIN','RESULT_NOT_RECEIVED')
            db.commit()
            rows=db.execute('SELECT r.request_id,r.body,o.due_unix_ms FROM feed_dry_run_requests r '
                'LEFT JOIN scheduled_occurrences o USING(request_id) WHERE r.decision IS NULL ORDER BY r.rowid').fetchall()
            for identifier,body,due in rows:
                if json.loads(body).get('source')!='SCHEDULED': continue
                db.execute('INSERT OR IGNORE INTO scheduled_delivery(request_id,state) VALUES(?,?)',(identifier,'QUEUED'))
                delivery=db.execute('SELECT state,last_sent FROM scheduled_delivery WHERE request_id=?',(identifier,)).fetchone()
                if due is None or now*1000>due+60000:
                    self.finish(db,identifier,body,'EXPIRED','WINDOW_EXPIRED');db.commit();continue
                # An acknowledged attempt may still be running; no overlap or replay.
                active=db.execute("SELECT 1 FROM scheduled_delivery WHERE state='ACKNOWLEDGED' AND last_sent>?",(now-60,)).fetchone()
                s=self.bridge.last_status
                fresh=time.monotonic()-self.bridge.status_received_mono<2.5
                if active or not fresh or s.get('scheduled_protocol')!=1: db.commit();return
                if s.get('inspect_required') is True:
                    self.finish(db,identifier,body,'REJECTED','INSPECTION_REQUIRED');db.commit();continue
                ready=s.get('bench_state') in ('READY','MASS OK GATE?','CAT FAULT*')
                if not ready or s.get('demo_exited') is not False or s.get('dog_running') is True: db.commit();return
                if now-delivery[1]<1.5: db.commit();return
                # Persist SENT before UART write; retries use the same ID and MCU dedup.
                db.execute("UPDATE scheduled_delivery SET state='SENT',last_sent=?,attempts=attempts+1 WHERE request_id=?",(now,identifier))
                db.commit()
                self.bridge.send_cmd(ser,'feed_once '+identifier,'SCHEDULED_ACK_REQUIRED:'+identifier)
                return

