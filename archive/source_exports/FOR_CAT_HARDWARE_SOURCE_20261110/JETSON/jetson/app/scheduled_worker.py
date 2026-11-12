"""ASGI background schedule worker; SQLite atomic occurrence/inbox, no hardware API."""
import asyncio
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from threading import Event, RLock
import time
import uuid

from app.dry_run_requests import DryRunRequests
from app.meal_plans import MealPlans, PlanMissing, PlanConflict, evaluate_schedule, schedule_runtime_reason
from app.observability import get_logger, WarningLimiter
from app.schedule_gate import ScheduledRequestGate


class TransactionRequests:
    def __init__(self, db):
        self.db = db

    def enqueue(self, request_id, source, sub_source='', target_grams=35):
        return DryRunRequests.enqueue_in_transaction(self.db, request_id, source, sub_source, target_grams)


class ScheduledOccurrences:
    MAX_ROWS = 256

    def __init__(self, path):
        self.plans = MealPlans(path)
        self.path = self.plans.path
        with closing(self.plans.connect()) as db:
            DryRunRequests.ensure_schema(db)
            db.execute('CREATE TABLE IF NOT EXISTS scheduled_occurrences('
                       'occurrence_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,local_date TEXT NOT NULL,'
                       'due_unix_ms INTEGER NOT NULL,plan_revision INTEGER NOT NULL,request_id TEXT NOT NULL UNIQUE,'
                       'created_at TEXT NOT NULL,origin TEXT NOT NULL,UNIQUE(plan_id,local_date))')
            # Upgrade daily identity to scheduled-slot identity, retaining old receipts.
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='scheduled_occurrences'").fetchone()[0]
            if 'UNIQUE(plan_id,local_date)' in schema.replace(' ', ''):
                db.execute('BEGIN IMMEDIATE')
                db.execute('ALTER TABLE scheduled_occurrences RENAME TO scheduled_occurrences_daily_v1')
                db.execute('CREATE TABLE scheduled_occurrences('
                           'occurrence_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,local_date TEXT NOT NULL,'
                           'due_unix_ms INTEGER NOT NULL,plan_revision INTEGER NOT NULL,request_id TEXT NOT NULL UNIQUE,'
                           'created_at TEXT NOT NULL,origin TEXT NOT NULL,UNIQUE(plan_id,due_unix_ms))')
                db.execute('INSERT INTO scheduled_occurrences SELECT * FROM scheduled_occurrences_daily_v1')
                db.execute('DROP TABLE scheduled_occurrences_daily_v1')
            db.commit()

    def submit(self, plan_id, state, now, *, origin, expected_revision=None, clock=None):
        if origin not in ('WORKER', 'PREVIEW'):
            raise ValueError('invalid occurrence origin')
        with closing(self.plans.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT plan_id,body,revision,deleted FROM meal_plans WHERE plan_id=? AND deleted=0', (plan_id,)).fetchone()
            plan = self.plans.decode(row)
            if expected_revision is not None and plan['revision'] != expected_revision:
                raise PlanConflict('plan changed; reload before preview')
            if clock is not None:
                now = clock()  # recheck after acquiring SQLite write ownership
            result = evaluate_schedule(plan, state, now)
            result['mode'] = 'SCHEDULED_DRY_RUN'
            if result['reason'] != 'DUE':
                return result
            # A renamed/retried slot is the same meal. An explicitly retimed
            # plan is a new slot even if the earlier time already ran today.
            occurrence_id = 'occurrence_' + hashlib.sha256((plan_id+':'+str(result['due_unix_ms'])).encode()).hexdigest()[:48]
            old = db.execute('SELECT request_id,due_unix_ms,plan_revision,origin,occurrence_id FROM scheduled_occurrences WHERE plan_id=? AND due_unix_ms=?', (plan_id,result['due_unix_ms'])).fetchone()
            if old:
                stored = db.execute('SELECT body,decision FROM feed_dry_run_requests WHERE request_id=?', (old[0],)).fetchone()
                if stored is None:
                    raise ValueError('occurrence references missing canonical request')
                body = json.loads(stored[0])
                if body.get('source') != 'SCHEDULED' or body.get('target_grams') != 35 or body.get('actuator_execution') is not False or body.get('actual_dispensed_grams') is not None:
                    raise ValueError('invalid stored scheduled receipt')
                return {**result, 'candidate': True, 'reason': 'DUE_INSTANCE_DRY_RUN',
                        'occurrence_id': old[4], 'occurrence_state': 'ALREADY_SUBMITTED',
                        'occurrence_due_unix_ms': old[1], 'occurrence_plan_revision': old[2], 'origin': old[3],
                        'request': {'request': body, 'decision': json.loads(stored[1]) if stored[1] else None}}
            if db.execute('SELECT COUNT(*) FROM scheduled_occurrences').fetchone()[0] >= self.MAX_ROWS:
                raise OverflowError('scheduled occurrence ledger full; fail closed')
            queued = ScheduledRequestGate(TransactionRequests(db)).submit_due(
                plan_id, result['due_unix_ms'], int(now.timestamp()*1000), time_valid=True)
            assert queued['candidate'] is True
            db.execute('INSERT INTO scheduled_occurrences VALUES(?,?,?,?,?,?,?,?)',
                       (occurrence_id, plan_id, result['local_date'], result['due_unix_ms'], plan['revision'],
                        queued['request']['request']['request_id'], now.isoformat(), origin))
            db.commit()  # occurrence + canonical request are committed together
            return {**result, **queued, 'occurrence_id': occurrence_id,
                    'occurrence_state': 'SUBMITTED', 'origin': origin}

    def recent(self, limit=20):
        with closing(self.plans.connect()) as db:
            rows = db.execute('SELECT o.occurrence_id,o.plan_id,o.local_date,o.due_unix_ms,o.plan_revision,'
                              'o.request_id,o.created_at,o.origin,r.decision FROM scheduled_occurrences o '
                              'LEFT JOIN feed_dry_run_requests r ON o.request_id=r.request_id '
                              'ORDER BY o.created_at DESC,o.occurrence_id LIMIT ?', (limit,)).fetchall()
        keys = ('occurrence_id','plan_id','local_date','due_unix_ms','plan_revision','request_id','created_at','origin','decision')
        result = []
        for row in rows:
            item = dict(zip(keys, row))
            try:
                item['decision'] = json.loads(item['decision']) if item['decision'] else None
            except (ValueError, TypeError):
                item['decision'] = None
                item['decision_health'] = 'INVALID_STORED_DECISION'
            item.update(target_grams=35, actuator_execution=False, actual_dispensed_grams=None)
            result.append(item)
        return result


class ScheduledWorker:
    def __init__(self, path, snapshot, meal_lock, *, enabled=False, poll_seconds=2,
                 clock=lambda: datetime.now(timezone.utc)):
        if not 1 <= poll_seconds <= 30:
            raise ValueError('scheduled poll interval must be 1..30s')
        self.path, self.state_snapshot, self.meal_lock = Path(path), snapshot, meal_lock
        self.enabled, self.poll_seconds, self.clock = enabled, poll_seconds, clock
        self.worker_id = uuid.uuid4().hex
        self._status_lock, self._stop = RLock(), Event()
        self._wake, self._task, self._store = None, None, None
        self._last_poll_mono = None
        self._status = {'status': 'DISABLED' if not enabled else 'STARTING', 'running': False,
                        'last_poll_at': None, 'last_successful_poll_at': None, 'last_error': None,
                        'poll_count': 0, 'submitted_count': 0, 'duplicate_observations': 0,
                        'error_count': 0, 'last_occurrence_id': None, 'last_request_id': None}
        self.logger, self.limiter = get_logger(), WarningLimiter()

    def occurrences(self):
        if self._store is None:
            self._store = ScheduledOccurrences(self.path)
        return self._store

    def status(self):
        with self._status_lock:
            result = dict(self._status)
            age = time.monotonic()-self._last_poll_mono if self._last_poll_mono is not None else None
        if result['running'] and age is not None and age > self.poll_seconds*3+5:
            result['status'] = 'STALE'
        return {**result, 'enabled': self.enabled, 'worker_id': self.worker_id, 'pid': os.getpid(),
                'mode': 'DRY_RUN_ONLY', 'timezone': 'Asia/Ho_Chi_Minh', 'poll_interval_seconds': self.poll_seconds,
                'last_poll_age_seconds': round(age,3) if age is not None else None,
                'target_grams': 35, 'auto_feed': False, 'auto_water': False, 'actuator_execution': False,
                'actual_dispensed_grams': None}

    def tick(self, now=None, state=None):
        if not self.enabled or self._stop.is_set():
            return []
        fixed_now, fixed_state = now is not None, state is not None
        now = self.clock() if now is None else now
        with self._status_lock:
            self._status['poll_count'] += 1
            self._status['last_poll_at'] = now.isoformat()
            self._last_poll_mono = time.monotonic()
        outcomes, errors = [], []
        try:
            state = self.state_snapshot() if state is None else state
            with self.meal_lock:
                store = self.occurrences()
                plans = store.plans.list()
            if plans['errors']:
                errors.append('INVALID_STORED_PLAN_NOT_SCHEDULED')
            for plan in plans['plans']:
                if self._stop.is_set():
                    break
                # Cheap shared eligibility check, followed by an authoritative
                # transactional re-read (edits/deletes between these are safe).
                eligibility = evaluate_schedule(plan, state, now)
                if eligibility['reason'] != 'DUE':
                    continue
                try:
                    with self.meal_lock:
                        current_state = state if fixed_state else self.state_snapshot()
                        outcome = store.submit(plan['plan_id'], current_state, now, origin='WORKER',
                                               clock=None if fixed_now else self.clock)
                    outcomes.append(outcome)
                    if outcome.get('candidate'):
                        created = outcome['occurrence_state'] == 'SUBMITTED'
                        with self._status_lock:
                            self._status['submitted_count' if created else 'duplicate_observations'] += 1
                            self._status['last_occurrence_id'] = outcome['occurrence_id']
                            self._status['last_request_id'] = outcome['request']['request']['request_id']
                        if created:
                            self.logger.info('Scheduled occurrence committed: '+outcome['occurrence_id'], extra={
                                'component':'scheduled_worker','event_type':'SCHEDULED_DRY_RUN_CREATED',
                                'request_id':outcome['request']['request']['request_id']})
                except PlanMissing:
                    continue
                except Exception as error:
                    errors.append(type(error).__name__+': '+str(error)[:160])
        except Exception as error:
            errors.append(type(error).__name__+': '+str(error)[:160])
        health = 'RUNNING'
        if errors:
            health = 'DEGRADED'
            self.limiter.warn(self.logger, 'scheduled_error', errors[0], {'component':'scheduled_worker','event_type':'SCHEDULED_WORKER_ERROR'})
        else:
            health = {'TIME_INVALID':'WAITING_TIME_VALID','ESP32_UNAVAILABLE_NO_QUEUE':'WAITING_ESP32',
                      'SAFETY_STATE_UNKNOWN_OR_UNSAFE_NO_QUEUE':'WAITING_SAFE_STATE'}.get(schedule_runtime_reason(state), 'RUNNING')
        with self._status_lock:
            self._status.update(status=health, last_error=errors[0] if errors else None)
            self._status['error_count'] += len(errors)
            if not errors:
                self._status['last_successful_poll_at'] = now.isoformat()
        return outcomes

    async def start(self):
        if not self.enabled or self._task is not None:
            return
        self._stop.clear()
        self._wake = asyncio.Event()
        with self._status_lock:
            self._status['running'] = True
        self._task = asyncio.create_task(self._run(), name='scheduled-dry-run-worker')

    async def _run(self):
        while not self._stop.is_set():
            await asyncio.to_thread(self.tick)
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass

    async def stop(self):
        self._stop.set()
        if self._wake:
            self._wake.set()
        if self._task:
            await self._task
            self._task = None
        with self._status_lock:
            self._status['running'] = False
            self._status['status'] = 'STOPPED' if self.enabled else 'DISABLED'
