"""Bounded Meal Plans and shared due evaluation; all execution remains DRY RUN."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schedule_gate import ScheduledRequestGate

VIETNAM = timezone(timedelta(hours=7), 'Asia/Ho_Chi_Minh')
ID = r'^[A-Za-z0-9_-]{1,64}$'


class PlanDefinition(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=64)
    local_time: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    weekdays: list[Annotated[int, Field(strict=True, ge=0, le=6)]] = Field(min_length=1, max_length=7)
    enabled: bool = False
    target_grams: Annotated[int, Field(strict=True, ge=35, le=35)] = 35
    timezone: Literal['Asia/Ho_Chi_Minh'] = 'Asia/Ho_Chi_Minh'

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('nonempty printable name required')
        return value

    @field_validator('weekdays')
    @classmethod
    def unique_days(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('weekdays must be unique; Monday=0')
        return sorted(value)


class CreatePlan(PlanDefinition):
    plan_id: str = Field(pattern=ID)


class UpdatePlan(PlanDefinition):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]


class Revision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: Annotated[int, Field(strict=True, ge=1)]


class PlanMissing(Exception):
    pass


class PlanConflict(Exception):
    pass


def strict_object(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate configuration key')
        data[key] = value
    return data


class MealPlans:
    MAX_ACTIVE = 32
    MAX_IDENTITIES = 256  # tombstones prevent stale create retries resurrecting deleted plans

    def __init__(self, path):
        self.path = Path(path).resolve()
        with closing(self.connect()) as db:
            db.execute('CREATE TABLE IF NOT EXISTS meal_plans('
                       'plan_id TEXT PRIMARY KEY,body TEXT NOT NULL,revision INTEGER NOT NULL,deleted INTEGER NOT NULL DEFAULT 0)')
            db.commit()

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=.5)

    @staticmethod
    def decode(row):
        if row is None:
            raise PlanMissing('meal plan not found')
        plan_id, body, revision, deleted = row
        if not re.fullmatch(ID, plan_id) or type(revision) is not int or revision < 1 or deleted != 0 or len(body) > 4096:
            raise ValueError('invalid stored meal plan')
        value = json.loads(body, object_pairs_hook=strict_object)
        definition = PlanDefinition.model_validate(value)
        return {'plan_id': plan_id, 'revision': revision, **definition.model_dump(),
                'mode': 'SCHEDULED_DRY_RUN', 'actuator_execution': False}

    def list(self):
        plans, errors = [], []
        with closing(self.connect()) as db:
            rows = db.execute('SELECT plan_id,body,revision,deleted FROM meal_plans WHERE deleted=0 ORDER BY plan_id LIMIT 257').fetchall()
        if len(rows) > self.MAX_ACTIVE:
            raise ValueError('meal plan configuration limit exceeded')
        for row in rows:
            try:
                plans.append(self.decode(row))
            except (ValueError, TypeError):
                errors.append({'plan_id': row[0], 'reason': 'INVALID_STORED_PLAN_NOT_SCHEDULED'})
        return {'plans': plans, 'errors': errors, 'mode': 'SCHEDULED_DRY_RUN',
                'autonomous_worker_enabled': False, 'actuator_execution': False}

    def get(self, plan_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT plan_id,body,revision,deleted FROM meal_plans WHERE plan_id=? AND deleted=0', (plan_id,)).fetchone()
        return self.decode(row)

    def create(self, request):
        definition = PlanDefinition.model_validate(request.model_dump(exclude={'plan_id'}))
        body = json.dumps(definition.model_dump(), sort_keys=True, separators=(',', ':'))
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT plan_id,body,revision,deleted FROM meal_plans WHERE plan_id=?', (request.plan_id,)).fetchone()
            if old:
                if old[3] or old[1] != body:
                    raise PlanConflict('plan ID already used; reload current plans')
                return self.decode(old)
            active, total = db.execute('SELECT COALESCE(SUM(deleted=0),0),COUNT(*) FROM meal_plans').fetchone()
            if active >= self.MAX_ACTIVE or total >= self.MAX_IDENTITIES:
                raise OverflowError('meal plan ledger full; fail closed')
            db.execute('INSERT INTO meal_plans VALUES(?,?,1,0)', (request.plan_id, body))
            db.commit()
        return self.get(request.plan_id)

    def update(self, plan_id, request):
        definition = PlanDefinition.model_validate(request.model_dump(exclude={'expected_revision'}))
        body = json.dumps(definition.model_dump(), sort_keys=True, separators=(',', ':'))
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,deleted FROM meal_plans WHERE plan_id=?', (plan_id,)).fetchone()
            if row is None or row[1]:
                raise PlanMissing('meal plan not found')
            if row[0] != request.expected_revision:
                raise PlanConflict('plan changed; reload before editing')
            db.execute('UPDATE meal_plans SET body=?,revision=revision+1 WHERE plan_id=?', (body, plan_id))
            db.commit()
        return self.get(plan_id)

    def delete(self, plan_id, expected_revision):
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,deleted FROM meal_plans WHERE plan_id=?', (plan_id,)).fetchone()
            if row is None:
                raise PlanMissing('meal plan not found')
            if row[1]:
                return {'deleted': True, 'plan_id': plan_id, 'actuator_execution': False}
            if row[0] != expected_revision:
                raise PlanConflict('plan changed; reload before deleting')
            db.execute('UPDATE meal_plans SET deleted=1,revision=revision+1 WHERE plan_id=?', (plan_id,))
            db.commit()
        return {'deleted': True, 'plan_id': plan_id, 'actuator_execution': False}


def preview_plan(plan, requests, state, now):
    """Compatibility helper: both callers use the same due/safety evaluation."""
    result = evaluate_schedule(plan, state, now)
    if result['reason'] != 'DUE':
        return result
    gate = ScheduledRequestGate(requests)
    return {**result, **gate.submit_due(plan['plan_id'], result['due_unix_ms'],
                                       int(now.timestamp()*1000), time_valid=True)}


def schedule_runtime_reason(state):
    if state.get('time', {}).get('time_valid') is not True:
        return 'TIME_INVALID'
    esp = state.get('esp32', {})
    if state.get('data_source') != 'REAL' or esp.get('connected') is not True or (
            'health' in esp and esp['health'] != 'ESP32_CONNECTED') or (
            'stale' in esp and esp['stale'] is not False):
        return 'ESP32_UNAVAILABLE_NO_QUEUE'
    safety = state.get('safety', {})
    if not all(safety.get(key) is False for key in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water', 'actuator_execution')) or type(safety.get('actuator_outputs_enabled')) is not int or safety['actuator_outputs_enabled'] != 0:
        return 'SAFETY_STATE_UNKNOWN_OR_UNSAFE_NO_QUEUE'
    return None


def evaluate_schedule(plan, state, now):
    result = {'candidate': False, 'plan_id': plan['plan_id'], 'plan_revision': plan['revision'],
              'actuator_execution': False, 'actual_dispensed_grams': None, 'target_grams': 35,
              'mode': 'SCHEDULED_DRY_RUN', 'clock_source': 'JETSON_SYSTEM_CLOCK'}
    if state.get('time', {}).get('time_valid') is not True:
        return {**result, 'reason': 'TIME_INVALID'}
    if now.tzinfo is None:
        raise ValueError('timezone-aware canonical clock required')
    local = now.astimezone(VIETNAM)
    hour, minute = map(int, plan['local_time'].split(':'))
    due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    result.update(due_at=due.isoformat(), observed_at=now.isoformat(),
                  local_date=local.date().isoformat(), due_unix_ms=int(due.timestamp()*1000))
    if not plan['enabled']:
        return {**result, 'reason': 'PLAN_DISABLED'}
    if local.weekday() not in plan['weekdays']:
        return {**result, 'reason': 'NOT_SCHEDULED_TODAY'}
    blocker = schedule_runtime_reason(state)
    if blocker:
        return {**result, 'reason': blocker}
    delta = int(now.timestamp()*1000) - result['due_unix_ms']
    if delta < 0:
        return {**result, 'reason': 'NOT_DUE'}
    if delta > 60000:
        return {**result, 'reason': 'MISSED_WINDOW_NO_CATCHUP'}
    return {**result, 'reason': 'DUE'}
