#!/usr/bin/env python3
"""Live bidirectional ESP32-S3 <-> SQLite <-> AI bridge for ForCat on Jetson."""
from contextlib import closing
from datetime import datetime, timezone
import glob
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import serial
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.water_control import init as init_water, Dispatcher as WaterDispatcher
from fc_bridge_storage import BridgeStorage
from fc_auto_cat_gate import block_reason as cat_device_block_reason

SPECS = {
    'HC_SR04_1': ('HC-SR04', 'CAT_APPROACH', 12, 13, 'near_cm'),
    'HC_SR04_2': ('HC-SR04', 'TBD', 16, 17, 'hc2_cm'),
    'JSN_SR04T_1': ('JSN-SR04T', 'WATER_LEVEL', 14, 15, 'food_distance_cm'),
    'JSN_SR04T_2': ('JSN-SR04T', 'TBD', 18, 10, 'water_distance_cm'),
}

DB_PATH = Path('/home/toan/for_cat/jetson/data/events.db')
CMD_FILE = Path('/tmp/for_cat_cmd.txt')
FOOD_MODE_FILE = Path('/tmp/for_cat_food_mode.txt')


def read_boot_id() -> str:
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    except OSError:
        return 'unknown-boot-id'


class SystemClockGate:
    """Confirm this boot's clock once; retain trust offline while time is continuous."""
    def __init__(self, boot_id, marker, probe=None):
        self.boot_id, self.marker = boot_id, Path(marker)
        self.probe = probe or self.ntp_synchronized
        self.trusted, self.previous = False, None
        self.last_probe = float('-inf')
        try:
            saved = json.loads(self.marker.read_text())
            wall_delta = time.time() - saved['wall']
            mono_delta = time.monotonic() - saved['mono']
            self.trusted = (saved['boot_id'] == boot_id and mono_delta >= 0
                            and abs(wall_delta - mono_delta) <= 2.0)
        except (OSError, ValueError, KeyError, TypeError):
            pass

    @staticmethod
    def ntp_synchronized():
        try:
            result = subprocess.run(['timedatectl', 'status'], capture_output=True,
                                    text=True, timeout=1,
                                    env={**os.environ, 'LC_ALL': 'C'})
            return result.returncode == 0 and any(line.strip() in (
                'System clock synchronized: yes', 'NTP synchronized: yes')
                for line in result.stdout.splitlines())
        except (OSError, subprocess.TimeoutExpired):
            return False

    def valid(self):
        wall, mono = time.time(), time.monotonic()
        if self.previous is not None:
            dw, dm = wall-self.previous[0], mono-self.previous[1]
            if dm < 0 or abs(dw-dm) > 2.0:
                self.trusted, self.last_probe = False, mono
                try:
                    self.marker.unlink(missing_ok=True)
                except OSError:
                    pass
        self.previous = wall, mono
        if not self.trusted and mono-self.last_probe >= 5:
            self.last_probe = mono
            if self.probe():
                self.trusted = True
                temp = self.marker.with_suffix('.'+str(os.getpid())+'.tmp')
                try:
                    temp.write_text(json.dumps({'boot_id': self.boot_id,
                                                'wall': wall, 'mono': mono}))
                    temp.replace(self.marker)
                except OSError:
                    pass
        return self.trusted


def find_serial_device() -> str | None:
    configured=os.environ.get('FORCAT_ESP32_PORT','').strip()
    if configured:
        return configured if Path(configured).is_char_device() else None
    by_id = sorted(glob.glob('/dev/serial/by-id/*'))
    if by_id:
        return str(Path(by_id[0]).resolve())
    for pattern in ('/dev/ttyACM*', '/dev/ttyUSB*'):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


def open_serial_device(dev):
    ser=serial.Serial(port=dev,baudrate=115200,timeout=0.1,write_timeout=0.5,dsrdtr=False,rtscts=False)
    if not dev.startswith('/dev/ttyTHS'):
        ser.dtr=False
        ser.rts=False
    return ser


class SerialLineBuffer:
    # readline() can return a partial line when its 100ms timeout expires.
    # A status frame takes longer than 100ms at 115200 baud.
    def __init__(self):
        self.pending=bytearray()
        self.discarding=False
    def feed(self,chunk):
        lines=[]
        for byte in chunk:
            if byte==10:
                if not self.discarding:
                    lines.append(self.pending.decode('utf-8',errors='replace').strip())
                self.pending.clear();self.discarding=False
            elif not self.discarding:
                self.pending.append(byte)
                if len(self.pending)>16384:
                    self.pending.clear();self.discarding=True
        return lines


def make_canonical_decision(req_id: str, req_body_str: str, qualification: str = 'DISPATCHED_TO_ESP32_35G') -> str:
    try:
        req = json.loads(req_body_str) if req_body_str else {}
    except ValueError:
        req = {}
    return json.dumps({
        'request_id': req_id,
        'source': req.get('source', 'MANUAL'),
        'sub_source': req.get('sub_source', 'APP'),
        'target_grams': 35,
        'status': 'DRY_RUN_BLOCKED',
        'reason': 'UNATTENDED_SAFE_MODE',
        'qualification_reason': qualification,
        'decided_at': datetime.now(timezone.utc).isoformat(),
        'actuator_execution': False,
        'actual_dispensed_grams': None,
    }, separators=(',', ':'))


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
        # Never dispatch a wall-clock schedule using the stale boot-time date.
        if not self.bridge.clock.valid():
            return
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


class BridgeRunner:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.boot_id = read_boot_id()
        self.clock = SystemClockGate(self.boot_id, db_path.with_name('clock_trust_v1.json'))
        self.frames_ok = 0
        self.frames_bad = 0
        self.reconnects = 0
        self.dog_triggers = 0
        self.cat_triggers = 0
        self.last_button_count = 0
        self.us_history = {
            k: {'timeout_count': 0, 'last_valid_cm': None, 'last_valid_ms': None}
            for k in SPECS
        }
        self.last_dog_trigger_mono = 0.0
        self.last_cat_trigger_mono = 0.0
        self.last_host_ping_mono = float('-inf')
        self.last_ai_oled = 'NONE'
        self.last_ai_oled_mono = 0.0
        self.cat_consecutive = 0
        self.dog_candidate_stamp = None
        self.dog_candidate_frames = 0
        self.dog_candidate_started_mono = 0.0
        self.active_food_cmd = '1a'
        self.last_selected_food = None
        self.last_food_sync_mono = 0.0
        self.last_status = {}
        self._init_db()
        self.storage=BridgeStorage(self.db_path)
        self.status_received_mono = float("-inf")
        self.scheduled_delivery = ScheduledDelivery(self)
        init_water(self.db_path)
        self.water_dispatcher = WaterDispatcher(self)

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path, timeout=2.0)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute(
                'CREATE TABLE IF NOT EXISTS esp32_latest('
                'id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)'
            )
            db.execute(
                'CREATE TABLE IF NOT EXISTS esp32_events('
                'seq INTEGER PRIMARY KEY AUTOINCREMENT, '
                'kind TEXT NOT NULL, occurred_at TEXT NOT NULL, body TEXT NOT NULL)'
            )
            row = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='feed_dry_run_requests'"
            ).fetchone()
            if row:
                all_reqs = db.execute(
                    'SELECT request_id, body, decision FROM feed_dry_run_requests'
                ).fetchall()
                for req_id, req_body, dec_str in all_reqs:
                    # Pending schedules belong to the durable ACK dispatcher.
                    # Startup normalization must not claim delivery before UART ACK.
                    if not dec_str:
                        try:
                            if json.loads(req_body).get('source') == 'SCHEDULED':
                                continue
                        except (ValueError, TypeError, AttributeError):
                            pass
                    need_fix = False
                    if not dec_str:
                        need_fix = True
                    else:
                        try:
                            dec = json.loads(dec_str)
                            if dec.get('status') != 'DRY_RUN_BLOCKED' or dec.get('request_id') != req_id:
                                need_fix = True
                        except ValueError:
                            need_fix = True
                    if need_fix:
                        fixed = make_canonical_decision(req_id, req_body)
                        db.execute(
                            'UPDATE feed_dry_run_requests SET decision=? WHERE request_id=?',
                            (fixed, req_id),
                        )
            db.commit()

    def log_event(self, kind: str, details: dict):
        now_iso = datetime.now(timezone.utc).isoformat()
        body = json.dumps(details, separators=(',', ':'))
        try:
            if not self.storage.event(kind,now_iso,body):
                print('[bridge] event deferred to durable outbox: '+kind,flush=True)
        except OSError as exc:
            print('[bridge] event outbox storage error: '+str(exc),file=sys.stderr,flush=True)

    def _build_ultrasonic(self, msg: dict, stamp_ms: int) -> dict:
        channels = {}
        for key, (kind, role, trig, echo, cm_field) in SPECS.items():
            hist = self.us_history[key]
            raw_cm = msg.get(cm_field)
            valid = (
                isinstance(raw_cm, (int, float))
                and not isinstance(raw_cm, bool)
                and math.isfinite(raw_cm)
                and 0.0 < float(raw_cm) <= 450.0
            )
            if valid:
                cm_val = round(float(raw_cm), 2)
                hist['last_valid_cm'] = cm_val
                hist['last_valid_ms'] = stamp_ms
                state = 'HEALTHY'
                timeout = False
            else:
                cm_val = None
                hist['timeout_count'] = (hist['timeout_count'] + 1) & 0xFFFFFFFF
                state = 'TIMEOUT'
                timeout = True

            channels[key] = {
                'sensor_id': key,
                'type': kind,
                'role': role,
                'trigger_gpio': trig,
                'echo_gpio': echo,
                'wired': True,
                'configured': True,
                'enabled': True,
                'distance_cm': cm_val,
                'valid': valid,
                'timeout': timeout,
                'stale': False,
                'state': state,
                'last_update': stamp_ms,
                'sample_age_ms': 0,
                'last_valid_distance_cm': hist['last_valid_cm'],
                'last_valid_update': hist['last_valid_ms'],
                'timeout_count': hist['timeout_count'],
            }
        return channels

    def handle_status(self, msg: dict, device_path: str):
        self.frames_ok += 1
        self.last_status = msg
        self.status_received_mono = time.monotonic()
        now_mono_ms = int(time.monotonic() * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()
        stamp_ms = int(msg.get('ms') or 0) & 0xFFFFFFFF

        btn_count = int(msg.get('button_count') or 0) & 0xFFFFFFFF
        btn_last_ms = int(msg.get('button_last_ms') or 0) & 0xFFFFFFFF
        if btn_count > self.last_button_count:
            self.last_button_count = btn_count
            self.log_event('manual_button_feed', {
                'button_gpio': 21,
                'request_count': btn_count,
                'last_press_ms': btn_last_ms,
                'target_grams': 35,
            })

        ultrasonic = self._build_ultrasonic(msg, stamp_ms)
        hc1 = ultrasonic['HC_SR04_1']
        jsn1 = ultrasonic['JSN_SR04T_1']

        raw_counts = msg.get('raw')
        if not isinstance(raw_counts, int) or isinstance(raw_counts, bool):
            raw_counts = 0
        raw_counts = max(-8388608, min(8388607, raw_counts))
        raw_ok = bool(msg.get('raw_valid') is True)

        hx_health_in = str(msg.get('hx_health') or 'HEALTHY')
        if hx_health_in not in (
            'NOT_CONFIGURED', 'NOT_CONNECTED', 'NOT_CALIBRATED',
            'INITIALIZING', 'HEALTHY', 'DEGRADED', 'FAULT', 'NOT_WIRED'
        ):
            hx_health_in = 'HEALTHY' if raw_ok else 'DEGRADED'

        display_g = msg.get('display_g')
        grams = display_g if isinstance(display_g, (int, float)) and not isinstance(display_g, bool) else msg.get('grams')
        if isinstance(grams, (int, float)) and not isinstance(grams, bool) and math.isfinite(grams):
            grams = round(float(grams), 2)
        else:
            grams = None

        signed_g = msg.get('signed_g')
        if isinstance(signed_g, (int, float)) and not isinstance(signed_g, bool) and math.isfinite(signed_g):
            signed_g = round(float(signed_g), 2)
        else:
            signed_g = grams

        bench_state = str(msg.get('bench_state') or 'READY')
        meal_consumed_g = msg.get('meal_consumed_g')
        if isinstance(meal_consumed_g, (int, float)) and math.isfinite(meal_consumed_g):
            meal_consumed_g = round(float(meal_consumed_g), 2)
        else:
            meal_consumed_g = None

        near_stable = bool(
            hc1['valid']
            and hc1['distance_cm'] is not None
            and 5.0 <= hc1['distance_cm'] <= 20.0
        )

        fc_live = {
            'backup_enabled': msg.get('backup_enabled'),
            'backup_offline': msg.get('backup_offline'),
            'backup_storage_ok': msg.get('backup_storage_ok'),
            'backup_wait_clear': msg.get('backup_wait_clear'),
            'backup_active': msg.get('backup_active'),
            'scheduled_protocol': msg.get('scheduled_protocol'),
            'ai_oled': msg.get('ai_oled'),
            'tare_counts': msg.get('tare_counts'),
            'grams_per_count': msg.get('grams_per_count'),
            'grams': grams,
            'signed_g': signed_g,
            'bench_state': bench_state,
            'dog_running': bool(msg.get('dog_running') is True),
            'dispensed_g': msg.get('bench_delta_g'),
            'water_level_percent': msg.get('water_level_percent'),
            'meal_food': msg.get('meal_food') or ('FOOD_B' if self.active_food_cmd == '1b' else 'FOOD_A'),
            'meal_starting_g': msg.get('meal_starting_g'),
            'meal_remaining_g': msg.get('meal_remaining_g'),
            'meal_consumed_g': meal_consumed_g,
            'meal_preference': msg.get('meal_preference'),
            'meal_conclusion': msg.get('meal_conclusion'),
            'active_food_cmd': self.active_food_cmd,
        }

        fc_live.update({k:msg.get(k) for k in ('meal_schema_version', 'meal_phase', 'meal_id', 'meal_window_seconds', 'meal_elapsed_seconds', 'meal_stable', 'selected_food')})
        fc_live.update(demo_exited=msg.get('demo_exited'),inspect_required=msg.get('inspect_required'),device_feed_block_reason=cat_device_block_reason(msg,time.monotonic(),self.status_received_mono))
        fc_live.update({k:msg.get(k) for k in ('pump_auto_enabled','pump_auto_running','pump_auto_fault','pump_reason','pump_driver_verified','pump_test_running')})
        self.last_selected_food=msg.get('selected_food')

        is_open = bench_state in ('CAT OPENING', 'WAIT 30-40g', 'TEST SERVO OPEN')
        is_eating = bench_state in ('CAT OPENING', 'WAIT 30-40g', 'CAT CLOSING', 'MASS OK GATE?')

        telemetry = {
            'mode': 'FC_LIVE_BENCH',
            'monotonic_ms': stamp_ms,
            'ultrasonic_schema_version': 1,
            'ultrasonic': ultrasonic,
            'sensors': {
                'pir': {
                    'configured': False,
                    'motion': None,
                    'health': 'NOT_CONFIGURED',
                    'transition_count': None,
                },
                'approach': {
                    'configured': True,
                    'echo_ack': True,
                    'distance_valid': hc1['valid'],
                    'distance_cm': hc1['distance_cm'],
                    'health': 'HEALTHY' if hc1['valid'] else 'DEGRADED',
                    'timeout_count': hc1['timeout_count'],
                },
                'water_operational': {
                    'configured': True,
                    'echo_ack': True,
                    'distance_valid': jsn1['valid'],
                    'distance_cm': jsn1['distance_cm'],
                    'health': 'HEALTHY' if jsn1['valid'] else 'DEGRADED',
                    'timeout_count': jsn1['timeout_count'],
                },
                'hx711': {
                    'configured': True,
                    'raw_available': raw_ok,
                    'raw_counts': raw_counts,
                    'firmware_calibrated': msg.get('calibrated') is True,
                    'health': hx_health_in,
                },
                'oled': {
                    'configured': True,
                    'health': 'HEALTHY' if msg.get('oled_ok') is True else 'DEGRADED',
                },
                'button': {
                    'configured': True,
                    'pressed': bool(msg.get('button_pressed') is True),
                    'request_count': btn_count,
                    'last_press_ms': btn_last_ms if btn_last_ms > 0 else None,
                    'health': 'HEALTHY',
                },
            },
            'safety': {
                'servo_armed': False,
                'servo_state': 'CLOSED' if msg.get('physical_closed') is True else 'UNKNOWN',
                'pump_armed': False,
                'pump_state': 'OFF',
                'auto_feed': False,
                'auto_water': False,
                'actuator_outputs_enabled': 0,
                'actuator_execution': False,
            },
            'fc_live': fc_live,
        }

        payload = {
            'schema_version': 'esp32_bridge_v1',
            'host_boot_id': self.boot_id,
            'updated_monotonic_ms': now_mono_ms,
            'last_rx_monotonic_ms': now_mono_ms,
            'last_received_at': now_iso,
            'device': device_path,
            'serial_connected': True,
            'health': 'ESP32_CONNECTED',
            'time_valid': self.clock.valid(),
            'actuator_execution': False,
            'serial_tx_enabled': False,
            'telemetry_parse_error': None,
            'counters': {
                'frames_ok': self.frames_ok,
                'frames_bad': self.frames_bad,
                'reconnects': self.reconnects,
                'dog_triggers': self.dog_triggers,
                'cat_triggers': self.cat_triggers,
            },
            'decisions': {
                'mode': 'DRY_RUN_ONLY',
                'near_configured': True,
                'near_threshold_cm': 20.0,
                'near_stable': near_stable,
                'food_behavior': 'EATING' if is_eating else 'IDLE',
                'consumed_grams': meal_consumed_g,
                'water_request_preview': False,
                'water_reason': 'SKIPPED',
                'actuator_execution': False,
            },
            'telemetry': telemetry,
        }

        body = json.dumps(payload, separators=(',', ':'))
        if not self.storage.latest(body) and (self.storage.errors<=3 or self.storage.errors%100==0):
            print('[bridge] telemetry storage deferred; UART remains connected: '+str(self.storage.last_error),file=sys.stderr,flush=True)

    def send_cmd(self, ser: serial.Serial, cmd: str, reason: str):
        clean = cmd.strip()
        if not clean:
            return
        if clean in ('a', '1a'):
            self.active_food_cmd = '1a'
            FOOD_MODE_FILE.write_text('1a\n', encoding='utf-8')
        elif clean in ('b', '1b'):
            self.active_food_cmd = '1b'
            FOOD_MODE_FILE.write_text('1b\n', encoding='utf-8')
        ser.write((clean + '\n').encode('ascii', errors='ignore'))
        ser.flush()
        print(f'[bridge] TX -> ESP32: {clean!r} ({reason})', flush=True)
        self.log_event('serial_tx_command', {'cmd': clean, 'reason': reason})

    def publish_ai_display(self, ser, cls, confidence):
        label = cls if cls in ('CAT','DOG') and confidence >= 0.40 else 'NONE'
        if label != self.last_ai_oled or time.monotonic()-self.last_ai_oled_mono >= 1.5:
            self.last_ai_oled=label
            self.last_ai_oled_mono=time.monotonic()
            self.send_cmd(ser, {'CAT':'ai_cat','DOG':'ai_dog','NONE':'ai_none'}[label], 'OLED_RECOGNITION_'+label)

    def check_commands_and_ai(self, ser: serial.Serial):
        if time.monotonic()-self.last_host_ping_mono>=1.5:
            ser.write(b'jetson_ping\n')
            ser.flush()
            self.last_host_ping_mono=time.monotonic()

        try:
            self.water_dispatcher.tick(ser)
        except sqlite3.Error as exc:
            print('[bridge] water control storage retry: '+str(exc),flush=True)


        # 0. Sync food mode file if updated externally
        if FOOD_MODE_FILE.is_file():
            try:
                mode_val = FOOD_MODE_FILE.read_text(encoding='utf-8').strip().lower()
                if mode_val in ('1a', '1b'):
                    self.active_food_cmd = mode_val
            except OSError:
                pass

        expected='FOOD_B' if self.active_food_cmd=='1b' else 'FOOD_A'
        if self.last_selected_food is not None and self.last_selected_food!=expected and time.monotonic()-self.last_food_sync_mono>=1.5:
            self.last_food_sync_mono=time.monotonic()
            self.send_cmd(ser,'b' if expected=='FOOD_B' else 'a','RESTORE_SELECTED_FOOD')

        # 1. Manual command file (/tmp/for_cat_cmd.txt)
        if CMD_FILE.is_file():
            try:
                raw_cmds = CMD_FILE.read_text(encoding='utf-8')
                CMD_FILE.unlink(missing_ok=True)
                for line in raw_cmds.splitlines():
                    if line.strip():
                        self.send_cmd(ser, line.strip(), 'MANUAL_CMD_FILE')
            except OSError as exc:
                print(f'[bridge] cmd file error: {exc}', file=sys.stderr, flush=True)

        # 2. Check pending Web UI manual feed & scheduled feed requests in feed_dry_run_requests
        try:
            with closing(sqlite3.connect(self.db_path, timeout=0.5)) as db:
                row = db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='feed_dry_run_requests'"
                ).fetchone()
                if row:
                    pending = db.execute(
                        'SELECT request_id, body FROM feed_dry_run_requests WHERE decision IS NULL LIMIT 5'
                    ).fetchall()
                    for req_id, req_body in pending:
                        if json.loads(req_body).get('source') == 'SCHEDULED':
                            continue
                        decision = make_canonical_decision(req_id, req_body, 'DISPATCHED_TO_ESP32_35G')
                        db.execute(
                            'UPDATE feed_dry_run_requests SET decision=? WHERE request_id=?',
                            (decision, req_id),
                        )
                        db.commit()
                        self.send_cmd(ser, 'manual_feed', f'WEB_OR_SCHEDULE_FEED:{req_id}')
        except sqlite3.Error:
            pass

        try:
            self.scheduled_delivery.tick(ser)
        except sqlite3.Error as exc:
            print('[bridge] scheduled delivery retry:', exc, flush=True)

        # 3. Check live AI state in ai_latest
        try:
            with closing(sqlite3.connect(self.db_path, timeout=0.5)) as db:
                row = db.execute('SELECT body FROM ai_latest WHERE id=1').fetchone()
            if not row:
                return
            ai = json.loads(row[0])
        except (sqlite3.Error, ValueError, TypeError):
            return

        now_mono = time.monotonic()
        now_mono_ms = now_mono * 1000.0
        stamp = ai.get('updated_monotonic_ms')
        if (
            ai.get('health') != 'ONLINE'
            or ai.get('host_boot_id') != self.boot_id
            or not isinstance(stamp, (int, float))
            or (now_mono_ms - float(stamp)) > 2500.0
        ):
            self.publish_ai_display(ser, 'NONE', 0.0)
            self.cat_consecutive = 0
            self.dog_candidate_stamp = None
            self.dog_candidate_frames = 0
            self.dog_candidate_started_mono = 0.0
            return

        cls = ai.get('classification')
        conf = ai.get('confidence') or 0.0
        bench_state = str(self.last_status.get('bench_state') or 'READY')
        dog_running = bool(self.last_status.get('dog_running') is True)
        device_block=cat_device_block_reason(self.last_status,now_mono,self.status_received_mono)

        self.publish_ai_display(ser, cls, conf)

        # A single flickering DOG label must not abort an accepted CAT motion.
        # Confirm distinct, fresh AI observations, rather than polling one frame.
        dog_signal = cls == 'DOG' and conf >= 0.70
        if not dog_signal:
            self.dog_candidate_stamp = None
            self.dog_candidate_frames = 0
            self.dog_candidate_started_mono = 0.0
        elif stamp != self.dog_candidate_stamp:
            if self.dog_candidate_frames == 0:
                self.dog_candidate_started_mono = now_mono
            self.dog_candidate_stamp = stamp
            self.dog_candidate_frames += 1
        dog_confirmed = (
            dog_signal and self.dog_candidate_frames >= 3
            and (now_mono - self.dog_candidate_started_mono) >= 1.0
        )

        if dog_confirmed:
            self.cat_consecutive = 0
            if not dog_running and (now_mono - self.last_dog_trigger_mono) >= 2.5:
                self.last_dog_trigger_mono = now_mono
                self.dog_triggers += 1
                self.send_cmd(ser, '2', f'AI_DOG_DETECTED(conf={conf:.2f})')
        elif cls == 'CAT' and conf >= 0.40:
            self.cat_consecutive += 1
            if (
                self.cat_consecutive >= 2
                and device_block is None
                and (now_mono - self.last_cat_trigger_mono) >= 12.0
            ):
                self.last_cat_trigger_mono = now_mono
                self.cat_triggers += 1
                self.send_cmd(ser, '1', f'AI_CAT_DETECTED(conf={conf:.2f})')
        else:
            self.cat_consecutive = 0

    def run_forever(self):
        last_ai_poll = 0.0
        while True:
            dev = find_serial_device()
            if not dev:
                print('[bridge] waiting for ESP32 serial device...', flush=True)
                time.sleep(1.0)
                continue
            try:
                print(f'[bridge] opening {dev} @ 115200...', flush=True)
                ser = open_serial_device(dev)
                self.log_event('serial_connected', {'device': dev})
                try:
                    self.water_dispatcher.on_connect(ser)
                except sqlite3.Error as exc:
                    print('[bridge] water startup storage retry: '+str(exc),flush=True)

                line_buffer=SerialLineBuffer()
                while True:
                    raw = ser.readline()
                    for line in line_buffer.feed(raw):
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                msg = json.loads(line)
                                mtype = msg.get('type')
                                if mtype == 'status':
                                    self.handle_status(msg, dev)
                                elif mtype in ('scheduled_ack','scheduled_result'):
                                    self.scheduled_delivery.handle(msg)
                                    self.log_event(mtype,msg)
                                elif mtype == 'meal_preference':
                                    print(f'[bridge] meal_preference: {line}', flush=True)
                                    self.log_event('meal_preference', msg)
                                else:
                                    self.log_event(str(mtype or 'esp32_msg'), msg)
                            except ValueError:
                                self.frames_bad += 1
                        elif line:
                            print(f'[esp32] {line}', flush=True)

                    now = time.monotonic()
                    if (now - last_ai_poll) >= 0.15:
                        last_ai_poll = now
                        self.check_commands_and_ai(ser)
                        self.storage.flush()
            except (serial.SerialException, OSError) as exc:
                self.reconnects += 1
                print(f'[bridge] serial disconnected ({exc}), retrying...', file=sys.stderr, flush=True)
                time.sleep(1.0)


if __name__ == '__main__':
    BridgeRunner(DB_PATH).run_forever()
