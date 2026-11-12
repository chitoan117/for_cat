"""Read-only consumer of the single C++ serial owner's canonical SQLite state."""
import json
from pathlib import Path
import sqlite3
import time
from contextlib import closing
import math
import sys
from app.ultrasonic_state import validate_channels


def read_host_boot_id():
    """A missing kernel identity is unknown, never a generated replacement ID."""
    if sys.platform != 'linux':
        return None
    try:
        value = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
        return value if 0 < len(value) <= 128 else None
    except (OSError, UnicodeError):
        return None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate cache key')
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError('non-finite cache value: ' + value)


def decode_cached_object(body, max_bytes):
    if not isinstance(body, str) or len(body.encode('utf-8')) > max_bytes:
        raise ValueError('invalid or oversized cache body')
    data = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(data, dict):
        raise ValueError('cache body must be an object')
    return data


def validate_cached_telemetry(telemetry):
    """Check the cached normalized shape; the C++ bridge owns wire parsing."""
    if telemetry is None:
        return
    if not isinstance(telemetry, dict):
        raise ValueError('invalid cached telemetry')
    sensors = telemetry.get('sensors', {})
    safety = telemetry.get('safety', {})
    if not isinstance(sensors, dict) or not isinstance(safety, dict):
        raise ValueError('invalid cached sensor/safety shape')
    if 'ultrasonic' in telemetry:
        if telemetry.get('ultrasonic_schema_version')!=1:raise ValueError('ultrasonic schema')
        validate_channels(telemetry['ultrasonic'])
        stamp=telemetry.get('monotonic_ms')
        if type(stamp) is not int or not 0<=stamp<=0xffffffff:raise ValueError('ultrasonic report timestamp')
        for channel in telemetry['ultrasonic'].values():
            update=channel['last_update']
            if update is not None and (stamp-update)&0xffffffff!=channel['sample_age_ms']:raise ValueError('cached ultrasonic age mismatch')
    for key in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water', 'actuator_execution'):
        if key in safety and safety[key] is not False:
            raise ValueError('cached actuator safety mismatch')
    if 'actuator_outputs_enabled' in safety and (
            type(safety['actuator_outputs_enabled']) is not int or safety['actuator_outputs_enabled'] != 0):
        raise ValueError('cached actuator output mismatch')
    for role, sensor in sensors.items():
        if not isinstance(sensor, dict):
            raise ValueError('invalid cached sensor: ' + str(role))
        if 'health' in sensor and sensor['health'] not in (
                'NOT_CONFIGURED', 'NOT_CONNECTED', 'NOT_CALIBRATED', 'INITIALIZING',
                'HEALTHY', 'DEGRADED', 'FAULT', 'NOT_WIRED'):
            raise ValueError('invalid cached sensor health')
        for key in ('configured', 'distance_valid', 'raw_available', 'firmware_calibrated', 'pressed'):
            if key in sensor and type(sensor[key]) is not bool:
                raise ValueError('invalid cached sensor flag')
        if sensor.get('motion') is not None and type(sensor['motion']) is not bool:
            raise ValueError('invalid cached PIR level')
        for key in ('distance_cm', 'raw_counts'):
            value = sensor.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError('invalid cached sensor number')
        if 'distance_valid' in sensor:
            distance = sensor.get('distance_cm')
            if sensor['distance_valid'] != (distance is not None) or (
                    distance is not None and not 0 < distance <= 400):
                raise ValueError('cached distance/validity mismatch')
        raw = sensor.get('raw_counts')
        if raw is not None and not -8388608 <= raw <= 8388607:
            raise ValueError('cached raw count range')
        for key in ('transition_count', 'timeout_count', 'request_count', 'last_press_ms', 'last_transition_ms'):
            value = sensor.get(key)
            if value is not None and (type(value) is not int or not 0 <= value <= 0xffffffff):
                raise ValueError('invalid cached counter/timestamp')


class Esp32StateReader:
    def __init__(self, db_path, *, stale_seconds=3.0, monotonic=time.monotonic, boot_id=None):
        self.path = Path(db_path).resolve()
        self.stale_seconds = stale_seconds
        self.monotonic = monotonic
        self.boot_id = boot_id if boot_id is not None else read_host_boot_id()

    def _connect(self):
        return sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=0.2)

    def status(self):
        base = {'health': 'ESP32_DISCONNECTED', 'serial_connected': False,
                'telemetry': None, 'last_received_at': None, 'actuator_execution': False,
                'serial_tx_enabled': False, 'time_valid': False, 'reader_error': None,
                'telemetry_usable_now': False}
        try:
            if not self.boot_id:
                base['reader_error'] = 'HOST_BOOT_ID_UNAVAILABLE'
                return base
            with closing(self._connect()) as db:
                row = db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()
            if not row:
                return base
            data = decode_cached_object(row[0], 65536)
            if not isinstance(data, dict) or data.get('health') not in {
                    'ESP32_CONNECTED', 'ESP32_STALE', 'ESP32_DISCONNECTED', 'ESP32_BAD_TELEMETRY'}:
                raise ValueError('invalid bridge state')
            warning_only_tx = (data.get('serial_tx_enabled') is True and
                               data.get('serial_tx_scope') == 'DOG_WARNING_ONLY_NO_FEED_COMMANDS' and
                               data.get('dog_warning_tx_enabled') is True and
                               data.get('feed_tx_enabled') is False and data.get('pump_tx_enabled') is False)
            if data.get('feed_tx_enabled', False) is not False or data.get('pump_tx_enabled', False) is not False:
                raise ValueError('feed/pump transport must remain locked')
            if data.get('actuator_execution') is not False or not (
                    data.get('serial_tx_enabled') is False or warning_only_tx):
                raise ValueError('bridge safety contract mismatch')
            if type(data.get('serial_connected')) is not bool or type(data.get('time_valid')) is not bool:
                raise ValueError('invalid bridge flags')
            if data['health'] == 'ESP32_CONNECTED' and (
                    not data['serial_connected'] or not isinstance(data.get('telemetry'), dict)):
                raise ValueError('connected state lacks serial or telemetry')
            validate_cached_telemetry(data.get('telemetry'))
            if 'decisions' in data and not isinstance(data['decisions'], dict):
                raise ValueError('invalid cached decisions')
            if data.get('decisions', {}).get('actuator_execution', False) is not False:
                raise ValueError('cached decision execution mismatch')
            stamp = data.get('updated_monotonic_ms')
            if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
                raise ValueError('invalid bridge timestamp')
            age = self.monotonic() - stamp / 1000
            if not math.isfinite(age):
                raise ValueError('invalid bridge clock')
            if data.get('host_boot_id') != self.boot_id or age < 0:
                data['health'] = 'ESP32_DISCONNECTED'
                data['serial_connected'] = False
                data['time_valid'] = False
            elif age > self.stale_seconds:
                data['health'] = 'ESP32_STALE'
                data['serial_connected'] = False
                data['time_valid'] = False
            data['bridge_heartbeat_age_seconds'] = max(0, age)
            data['telemetry_usable_now'] = data['health'] == 'ESP32_CONNECTED'
            # Retained readings are history after staleness/disconnect, never fresh evidence.
            data['reader_error'] = None
            return data
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            base['reader_error'] = type(exc).__name__
            return base

    def events(self, limit=50):
        limit = max(1, min(int(limit), 100))
        try:
            with closing(self._connect()) as db:
                rows = db.execute('SELECT seq,kind,occurred_at,body FROM esp32_events '
                                  'ORDER BY seq DESC LIMIT ?', (limit,)).fetchall()
            events = []
            for row in rows:
                try:
                    details = decode_cached_object(row[3], 65536)
                except (ValueError, TypeError, RecursionError):
                    continue
                events.append({'seq': row[0], 'kind': row[1], 'timestamp': row[2], 'details': details})
            return events
        except (OSError, sqlite3.Error, ValueError, TypeError):
            return []


def owner_verification():
    """Declared physical facts are separate from transient driver health."""
    path = Path(__file__).resolve().parents[2] / 'config/hardware_current.json'
    try:
        if path.stat().st_size > 65536:
            return {'source': 'UNAVAILABLE'}
        config = decode_cached_object(path.read_text(), 65536)
        for key in ('approach', 'manual_feed_button'):
            if key in config and not isinstance(config[key], dict):
                return {'source': 'UNAVAILABLE'}
        return {'source': 'OWNER_CANONICAL_STATE', 'oled': config.get('oled'),
                'pir': config.get('pir'), 'hx711': config.get('hx711'),
                'approach': {'physical_ranging': config.get('approach', {}).get('physical_ranging')},
                'water_operational': config.get('operational_water'),
                'manual_button': {'physical_status': config.get('manual_feed_button', {}).get('physical_status')},
                 'inventory_not_wired': config.get('owner_reported_not_wired', []),
                 'ultrasonic':config.get('ultrasonic_inventory',{}),'rtc_status':config.get('rtc_status','UNKNOWN'),
                 'current_assembly_physical':'NOT_TESTED'}
    except (OSError, ValueError, TypeError, RecursionError):
        return {'source': 'UNAVAILABLE'}
