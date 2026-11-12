"""One web-facing state. REAL never substitutes mock numbers or classifications."""
import asyncio
from contextlib import suppress
from datetime import datetime, timezone
import logging


def unknown_state(source='REAL'):
    return {
        'schema_version': 'system_state_v1', 'data_source': source,
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'esp32': {'connected': False, 'serial_connected': False, 'health': 'ESP32_DISCONNECTED',
                  'device': None, 'last_telemetry_at': None, 'stale': False},
        'pir': {'motion': None, 'transition_count': None, 'health': 'UNKNOWN'},
        'approach': {'distance_cm': None, 'valid': False, 'health': 'UNKNOWN', 'timeout_count': None},
        'water_operational': {'distance_cm': None, 'valid': False, 'health': 'UNKNOWN', 'timeout_count': None},
        'weight': {'raw_counts': None, 'raw_available': False, 'calibrated': False,
                   'firmware_calibrated': None, 'grams': None, 'health': 'UNKNOWN', 'calibration_state': 'DEFERRED'},
        'oled': {'health': 'UNKNOWN'},
        'manual_button': {'pressed': None, 'request_count': None, 'last_press_ms': None, 'health': 'UNKNOWN',
                          'raw_level': None, 'debounced_level': None, 'state_source': 'UNKNOWN', 'state_device_ms': None},
        'safety': {'servo_armed': None, 'servo_state': 'UNKNOWN', 'pump_armed': None,
                   'pump_state': 'UNKNOWN', 'auto_feed': None, 'auto_water': None,
                   'actuator_outputs_enabled': None, 'actuator_execution': False},
        'food_reservoir_sensor': 'NOT_WIRED', 'food_reservoir_percent': None,
        'water_reservoir_sensor': 'NOT_WIRED', 'water_reservoir_percent': None,
        'ai': {'classification': 'UNKNOWN', 'health': 'DISCONNECTED', 'last_observation_at': None},
        'time': {'source': 'JETSON_SYSTEM_CLOCK', 'time_valid': False},
        'feed': {'target_grams': 35, 'actuator_execution': False, 'reason': 'UNATTENDED_SAFE_MODE'},
        'decisions': {'mode': 'DRY_RUN_ONLY', 'near_configured': False, 'near_threshold_cm': None,
                      'near_stable': False, 'food_behavior': 'UNKNOWN', 'consumed_grams': None,
                      'water_request_preview': False, 'water_reason': 'UNAVAILABLE', 'actuator_execution': False},
    }


class RealHardwareProvider:
    data_source = 'REAL'
    def __init__(self, esp32_reader, ai_reader=None):
        self.reader = esp32_reader
        self.ai_reader = ai_reader

    def snapshot(self):
        state = unknown_state()
        bridge = self.reader.status()
        fresh = bridge.get('telemetry_usable_now') is True
        link = bridge.get('health', 'ESP32_DISCONNECTED')
        state['esp32'].update(connected=fresh, serial_connected=bridge.get('serial_connected') is True,
                              health=link, device=bridge.get('device') or None,
                              last_telemetry_at=bridge.get('last_received_at'), stale=link == 'ESP32_STALE')
        state['time']['time_valid'] = bridge.get('time_valid') is True
        state['esp32']['counters'] = bridge.get('counters', {})
        if fresh:
            state['decisions'].update(bridge.get('decisions', {}))
            telemetry = bridge.get('telemetry') or {}
            sensors = telemetry.get('sensors', {})
            state['esp32']['mode'] = telemetry.get('mode')
            state['esp32']['monotonic_ms'] = telemetry.get('monotonic_ms')
            pir = sensors.get('pir', {})
            state['pir'].update(motion=pir.get('motion'), transition_count=pir.get('transition_count'),
                                health='CONFIGURED' if pir.get('configured') else 'NOT_CONFIGURED')
            for role in ('approach', 'water_operational'):
                sensor = sensors.get(role, {})
                valid = sensor.get('distance_valid') is True
                state[role].update(distance_cm=sensor.get('distance_cm') if valid else None,
                                   valid=valid, health=sensor.get('health', 'UNKNOWN'),
                                   timeout_count=sensor.get('timeout_count'))
            hx = sensors.get('hx711', {})
            state['weight'].update(raw_counts=hx.get('raw_counts'), raw_available=hx.get('raw_available') is True,
                                   firmware_calibrated=hx.get('firmware_calibrated'), health=hx.get('health', 'UNKNOWN'))
            # Canonical physical gram calibration remains DEFERRED. Never infer
            # grams from raw counts or treat a stored factor as physical validation.
            state['oled']['health'] = sensors.get('oled', {}).get('health', 'UNKNOWN')
            button = sensors.get('button', {})
            state['manual_button'].update(pressed=button.get('pressed'), request_count=button.get('request_count'),
                                          last_press_ms=button.get('last_press_ms'), health=button.get('health', 'NOT_CONFIGURED'),
                                          raw_level=button.get('button_raw_level'), debounced_level=button.get('button_debounced_level'),
                                          state_source=button.get('state_source', 'TELEMETRY'), state_device_ms=button.get('state_device_ms'))
            state['safety'].update(telemetry.get('safety', {}))
            state['safety']['actuator_execution'] = False
        else:
            unavailable = 'STALE' if link == 'ESP32_STALE' else 'DISCONNECTED' if link == 'ESP32_DISCONNECTED' else 'UNKNOWN'
            for role in ('pir', 'approach', 'water_operational', 'weight', 'oled', 'manual_button'):
                state[role]['health'] = unavailable
        if self.ai_reader:
            state['ai'] = self.ai_reader.status()
        # This is an observed behavior view, not the controller's safe idle state.
        # Missing AI must never be advertised as a verified animal IDLE state.
        state['decisions']['fsm_internal_state'] = state['decisions']['food_behavior']
        if state['ai'].get('health') != 'ONLINE' or (
                state['decisions']['food_behavior'] == 'EATING' and not state['weight']['calibrated']):
            state['decisions']['food_behavior'] = 'UNKNOWN'
        if state['ai'].get('health') != 'ONLINE' or not state['decisions']['near_configured']:
            state['decisions']['near_stable'] = False
        state['decisions']['actuator_execution'] = False
        state['decisions']['consumed_grams'] = None
        state['decisions']['eating_grams_validated'] = False
        return state


class MockProvider:
    """Explicit dev/test provider, never a fallback from REAL."""
    data_source = 'MOCK'
    def snapshot(self):
        return unknown_state('MOCK')


class SystemStateService:
    def __init__(self, provider):
        self.provider = provider
        self.clients = set()
        self.task = None
        self.provider_failure_count = 0
        self.last_provider_error = None

    def snapshot(self):
        try:
            state = self.provider.snapshot()
            self.last_provider_error = None
            return state
        except Exception as error:
            # One boundary for both REST and WS. Failed readers emit UNKNOWN,
            # keep the declared provider mode, and recover on the next poll.
            self.provider_failure_count += 1
            error_type = type(error).__name__
            if error_type != self.last_provider_error:
                logging.getLogger(__name__).error('SystemState provider unavailable: %s', error_type)
            self.last_provider_error = error_type
            state = unknown_state(getattr(self.provider, 'data_source', 'UNKNOWN'))
            state['provider_error'] = error_type
            state['provider_failure_count'] = self.provider_failure_count
            return state

    async def start(self):
        self.task = asyncio.create_task(self._publish())

    async def stop(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task

    async def _publish(self):
        while True:
            if self.clients:
                state = await asyncio.to_thread(self.snapshot)
                for queue in tuple(self.clients):
                    if queue.full():
                        queue.get_nowait()
                    queue.put_nowait(state)
            await asyncio.sleep(.1)

    def subscribe(self):
        if len(self.clients) >= 8:
            return None
        queue = asyncio.Queue(maxsize=1)
        self.clients.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.clients.discard(queue)
