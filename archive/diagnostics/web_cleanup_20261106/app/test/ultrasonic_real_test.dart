import 'dart:convert';

import 'package:feeder_demo/diagnostic_models.dart';
import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/status_model.dart';
import 'package:flutter_test/flutter_test.dart';

import 'state_fixture.dart';

Map<String, dynamic> data() {
  final s = fixture();
  s['ultrasonic_schema_version'] = 1;
  s['ultrasonic'] = {
    for (final row in [
      ('HC_SR04_1', 'HC-SR04', 'CAT_APPROACH', 12, 13),
      ('HC_SR04_2', 'HC-SR04', 'TBD', 16, 17),
      ('JSN_SR04T_1', 'JSN-SR04T', 'WATER_LEVEL', 14, 15),
      ('JSN_SR04T_2', 'JSN-SR04T', 'TBD', 18, 10),
    ])
      row.$1: <String, dynamic>{
        'type': row.$2,
        'role': row.$3,
        'trigger_gpio': row.$4,
        'echo_gpio': row.$5,
        'wired': true,
        'configured': true,
        'enabled': true,
        'valid': true,
        'timeout': false,
        'stale': false,
        'state': 'HEALTHY',
        'distance_cm': 30 + row.$4,
        'sample_age_ms': 100,
        'last_update': 1000,
        'firmware_supported': true,
      },
  };
  return s;
}

void main() {
  test(
    'backend outage retains declared pin map without obsolete RTC reservation',
    () {
      final rows = UltrasonicState.fromSystem(FeederState.unknown());
      expect(rows[1].triggerGpio, 16);
      expect(rows[1].echoGpio, 17);
      expect(rows[3].echoGpio, 10);
      expect(rows[1].proposedTrigger, isNull);
      expect(rows[1].wired, isNull);
      expect(rows[1].distanceCm, isNull);
    },
  );
  test(
    'four canonical channels keep identities pins and independent distances',
    () {
      final sensors = UltrasonicState.fromSystem(
        FeederState.decode(jsonEncode(data())),
      );
      expect(sensors.map((s) => s.sensorId), [
        'HC_SR04_1',
        'HC_SR04_2',
        'JSN_SR04T_1',
        'JSN_SR04T_2',
      ]);
      expect(sensors.map((s) => s.distanceCm), [42, 46, 44, 48]);
      expect(
        sensors.every(
          (s) =>
              s.proposedTrigger == null &&
              s.wired == true &&
              s.ageSeconds == .1,
        ),
        isTrue,
      );
    },
  );
  for (final state in [
    'TIMEOUT',
    'STALE',
    'UNKNOWN',
    'NOT_WIRED',
    'DISABLED',
  ]) {
    test('$state never becomes zero or last valid live distance', () {
      final d = data();
      final row = (d['ultrasonic'] as Map)['HC_SR04_2'] as Map;
      row['state'] = state;
      row['valid'] = false;
      row['distance_cm'] = null;
      row['last_valid_distance_cm'] = 35;
      final sensors = UltrasonicState.fromSystem(
        FeederState.decode(jsonEncode(d)),
      );
      expect(sensors[1].distanceCm, isNull);
      expect(sensors[0].distanceCm, 42);
      expect(sensors[1].state.code, state);
    });
  }
  test(
    'old firmware with newly wired #2 remains unknown with no invented reading',
    () {
      final d = data();
      final row = (d['ultrasonic'] as Map)['HC_SR04_2'] as Map;
      row['state'] = 'UNKNOWN';
      row['valid'] = false;
      row['distance_cm'] = null;
      row['sample_age_ms'] = null;
      row['enabled'] = null;
      row['firmware_supported'] = false;
      final s = UltrasonicState.fromSystem(
        FeederState.decode(jsonEncode(d)),
      )[1];
      expect(s.wired, isTrue);
      expect(s.state, AppStatus.unknown);
      expect(s.distanceCm, isNull);
    },
  );
  test(
    'stale link and invalid identity cannot show healthy canonical value',
    () {
      final d = data();
      (d['esp32'] as Map)['health'] = 'ESP32_STALE';
      expect(
        UltrasonicState.fromSystem(FeederState.decode(jsonEncode(d)))
            .every((s) => s.distanceCm == null),
        isTrue,
      );
      (d['esp32'] as Map)['health'] = 'ESP32_CONNECTED';
      ((d['ultrasonic'] as Map)['HC_SR04_1'] as Map)['echo_gpio'] = 7;
      final s = UltrasonicState.fromSystem(FeederState.decode(jsonEncode(d)))
          .first;
      expect(s.state, AppStatus.unknown);
      expect(s.distanceCm, isNull);
    },
  );
}
