"""New compatibility regressions against compiled C++ code, no Serial or old suite."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['FORCAT_NEW_TEST_OUT'])
EXE = OUT / 'bridge_probe.exe'
FRAMES = json.loads((ROOT / 'fixtures/manual_frames.json').read_text())
BASE = next(copy.deepcopy(x['payload']) for x in FRAMES if x['payload']['manual_station']['servo_close_us'] == 0 and x['payload']['manual_station']['pump_off_level'] == -1 and not x['payload']['manual_station']['fault_latched'])


class BridgeTests(unittest.TestCase):
    def call(self, args, expected=0):
        q = subprocess.run([str(EXE)] + [str(x) for x in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        with (OUT / 'native_invocations.jsonl').open('a') as f:
            f.write(json.dumps({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'command': [str(EXE)] + [str(x) for x in args], 'exit_code': q.returncode,
                'stdout_sha256': hashlib.sha256(q.stdout).hexdigest(), 'stderr': q.stderr.decode('utf-8', 'replace')})+'\n')
        self.assertEqual(q.returncode, expected, q.stderr.decode())
        return q.stdout.decode()

    def parse(self, data, expected=0, profile='manual'):
        path = OUT / (self._testMethodName + '.json')
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        text = self.call(['parse', path, profile], expected)
        return json.loads(text) if text else None

    def script(self, steps):
        path = OUT / (self._testMethodName + '.script.json')
        path.write_text(json.dumps({'steps': steps}))
        rows = [json.loads(x) for x in self.call(['script', path]).splitlines()]
        (OUT / (self._testMethodName + '.observed.json')).write_text(json.dumps(rows, indent=2))
        return rows

    @staticmethod
    def step(op, now, frame=None, **extra):
        out = {'case': op + '_' + str(now), 'op': op, 'host_ms': now}
        if frame is not None:
            out['data'] = json.dumps(frame) + '\n'
        out.update(extra)
        return out

    @staticmethod
    def frame(uptime, **manual):
        f = copy.deepcopy(BASE)
        f['monotonic_ms'] = uptime
        f['manual_station'].update(manual)
        return f

    def test_all_37_retained_firmware_frames_parse_without_relabeling(self):
        for retained in FRAMES:
            with self.subTest(origin=retained['origin']):
                result = self.parse(retained['payload'])
                self.assertEqual(result['wire_mode'], 'diag_manual_station')
                self.assertFalse(result['closed_loop_feed_capability'])
                self.assertFalse(result['bridge_serial_tx_enabled'])
                self.assertIsNone(result['safety']['physical_pump_on'])

    def test_explicit_profile_required_and_old_quad_still_accepted(self):
        self.parse(BASE, 1, 'quad')
        self.parse(BASE, 1, 'legacy')
        quad = json.loads((ROOT / 'fixtures/quad_legacy.json').read_text())
        self.parse(quad, 1)
        self.assertEqual(self.parse(quad, profile='quad')['mode'], 'diag_current_hardware')

    def test_old_sensor_only_actuator_guard_not_weakened(self):
        quad = json.loads((ROOT / 'fixtures/quad_legacy.json').read_text())
        quad['current_hardware']['servo_armed'] = True
        self.parse(quad, 3, 'quad')

    def test_wrong_identity_schema_pin_missing_sensor_rejected(self):
        for key, value in (('kit_firmware_id', 'OTHER'), ('kit_profile', 'diag_four_ultrasonic')):
            f = copy.deepcopy(BASE); f[key] = value; self.parse(f, 1)
        for key, value in (('schema_version', 2), ('boot_nonce', 0), ('servo_gpio', 5), ('pump_gpio', 6), ('buzzer_gpio', 7)):
            f = copy.deepcopy(BASE); f['manual_station'][key] = value; self.parse(f, 1)
        f = copy.deepcopy(BASE); del f['weight']; self.parse(f, 1)

    def test_duplicate_keys_truncated_oversize_and_wrong_types(self):
        text = json.dumps(BASE)
        self.parse('{"mode":"diag_manual_station",' + text[1:], 1)
        self.parse(text[:-8], 1)
        self.parse(' ' * 8193, 1)
        f = copy.deepcopy(BASE); f['manual_station']['servo_arms'] = True; self.parse(f, 1)

    def test_auto_authority_physical_claim_and_feedback_rejected(self):
        f = copy.deepcopy(BASE); f['manual_station']['automatic_execution'] = True; self.parse(f, 3)
        f = copy.deepcopy(BASE); f['current_hardware']['auto_feed'] = True; self.parse(f, 3)
        f = copy.deepcopy(BASE); f['manual_station']['physical_pass'] = True; self.parse(f, 1)
        f = copy.deepcopy(BASE); f['physical_pump_on'] = False; self.parse(f, 1)

    def test_valid_servo_motion_observed_not_authorized(self):
        f = self.frame(1000, session=1, last_sequence=2, servo_state='MOVING', servo_pulse_us=1550,
                       servo_close_us=1500, servo_open_us=1550, servo_arms=1)
        f['current_hardware'].update(servo_armed=True, servo_state='MOVING')
        r = self.parse(f)
        self.assertTrue(r['safety']['servo_armed'])
        self.assertFalse(r['safety']['automatic_execution_ready'])
        self.assertIsNone(r['safety']['actuator_outputs_enabled'])

    def test_interlock_mirrors_pulse_and_budget_faults(self):
        f = copy.deepcopy(BASE); f['current_hardware']['servo_armed'] = True; self.parse(f, 3)
        f = copy.deepcopy(BASE); f['manual_station']['servo_pulse_us'] = 1500; self.parse(f, 3)
        f = copy.deepcopy(BASE); f['manual_station']['servo_arms'] = 4; self.parse(f, 3)
        f = copy.deepcopy(BASE); f['manual_station'].update(servo_close_us=1000, servo_open_us=2000); self.parse(f, 3)

    def test_inert_and_conditional_pump_consistency(self):
        f = copy.deepcopy(BASE); f['manual_station']['pump_commanded_on'] = True; self.parse(f, 3)
        f = self.frame(1000, pump_supported=True, pump_off_level=0, pump_state='ON', pump_commanded_on=True, pump_pulses=1, session=1)
        f['current_hardware'].update(pump_armed=True, pump_state='ON')
        self.assertTrue(self.parse(f)['manual_station']['pump_commanded_on'])
        f['manual_station']['buzzer_enabled'] = f['manual_station']['buzzer_active'] = True
        self.parse(f, 3)

    def test_null_weight_and_distance_stay_null(self):
        r = self.parse(BASE)
        self.assertIsNone(r['sensors']['hx711']['raw_counts'])
        self.assertIsNone(r['sensors']['hx711']['grams'])
        self.assertIsNone(r['sensors']['approach']['distance_cm'])

    def test_fragments_noise_timeout_disconnect_and_reconnect(self):
        f = self.frame(1000); data = json.dumps(f) + '\n'
        rows = self.script([self.step('CONNECT', 1), self.step('RX', 2, data=data[:100]),
            self.step('RX', 3, data=data[100:]), self.step('RX', 4, data='MANUAL_RESULT boot=1 session=1 seq=2 result=ACCEPTED\n'),
            self.step('TICK', 4004), self.step('DISCONNECT', 4005), self.step('CONNECT', 4006),
            self.step('RX', 4007, f), self.step('RX', 4008, self.frame(1100))])
        self.assertEqual(rows[1]['health'], 'ESP32_STALE')
        self.assertEqual(rows[2]['health'], 'ESP32_CONNECTED')
        self.assertEqual(rows[3]['noise'], 1)
        self.assertIsNone(rows[4]['telemetry'])
        self.assertEqual(rows[5]['health'], 'ESP32_DISCONNECTED')
        self.assertIsNone(rows[6]['telemetry'])
        self.assertEqual(rows[7]['health'], 'ESP32_BAD_TELEMETRY')
        self.assertEqual(rows[8]['health'], 'ESP32_CONNECTED')

    def test_session_seq_budget_regression_and_new_session(self):
        frames = [self.frame(1000, session=1, last_sequence=5, servo_arms=1),
                  self.frame(1100, session=1, last_sequence=4, servo_arms=1),
                  self.frame(1200, session=2, last_sequence=0, servo_arms=1),
                  self.frame(1300, session=2, last_sequence=1, servo_arms=0)]
        rows = self.script([self.step('CONNECT', 1)] + [self.step('RX', i+10, f) for i, f in enumerate(frames)])
        self.assertEqual([r['accepted'] for r in rows], [0, 1, 1, 2, 2])

    def test_new_boot_needs_boundary_and_retired_boot_cannot_replay(self):
        a = self.frame(1000); b = self.frame(10, boot_nonce=a['manual_station']['boot_nonce']+1)
        rows = self.script([self.step('CONNECT', 1), self.step('RX', 2, a), self.step('RX', 3, b),
                            self.step('STARTUP', 4), self.step('RX', 5, b), self.step('STARTUP', 6), self.step('RX', 7, a)])
        self.assertEqual(rows[2]['accepted'], 1)
        self.assertEqual(rows[4]['accepted'], 2)
        self.assertEqual(rows[6]['accepted'], 2)

    def test_frozen_uptime_and_host_clock_regression_never_fresh(self):
        f = self.frame(1000)
        rows = self.script([self.step('CONNECT', 1), self.step('RX', 100, f), self.step('RX', 3000, f),
                            self.step('TICK', 3200), self.step('RX', 99, self.frame(1100))])
        self.assertEqual(rows[3]['health'], 'ESP32_STALE')
        self.assertEqual(rows[4]['health'], 'ESP32_BAD_TELEMETRY')

    def test_fault_resurrection_and_unsafe_latch_survive_reconnect(self):
        fault = self.frame(1000, fault_latched=True, servo_state='FAULT')
        fault['current_hardware']['servo_state'] = 'FAULT'
        rows = self.script([self.step('CONNECT', 1), self.step('RX', 2, fault),
                            self.step('RX', 3, self.frame(1100)), self.step('DISCONNECT', 4),
                            self.step('CONNECT', 5), self.step('RX', 6, self.frame(1200))])
        self.assertEqual(rows[2]['health'], 'ESP32_BAD_TELEMETRY')
        self.assertEqual(rows[-1]['health'], 'ESP32_BAD_TELEMETRY')
        self.assertIsNone(rows[-1]['telemetry'])

    def test_actual_cli_default_and_manual_never_enable_tx(self):
        r = json.loads(self.call(['options', '--firmware-profile', 'diag_manual_station']))
        self.assertTrue(r['explicit_manual']); self.assertFalse(r['would_open_serial']); self.assertFalse(r['serial_tx_enabled'])
        self.call(['options', '--firmware-profile', 'diag_manual_station', '--dog-warning', '1'], 1)
        self.call(['options', '--firmware-profile', 'HX711_REFERENCE'], 1)


if __name__ == '__main__':
    unittest.main()
