import 'dart:convert';
import 'package:feeder_demo/feeder_state.dart';
import 'package:flutter_test/flutter_test.dart';
import 'state_fixture.dart';

void main() {
  test('unknown and disconnected values never become mock percentages/grams', () {
    final state = FeederState.unknown();
    expect(state.source, 'REAL'); expect(state.online, isFalse); expect(state.grams, isNull);
    expect(state.inventory('food'), isNull); expect(state.classification, 'UNKNOWN');
    final old = FeederState.decode(jsonEncode(fixture(connected: false)));
    expect(old.distance('approach'), isNull); expect(old.rawCounts, isNull);
  });
  test('real data preserves calibrated wrapper range but never converts raw to grams', () {
    final data = fixture(); (data['weight'] as Map)['grams'] = 999;
    final state = FeederState.decode(jsonEncode(data));
    expect(state.distance('approach'), 24.8); expect(state.health('approach'), 'NOT_CALIBRATED');
    expect(state.rawCounts, -675000); expect(state.grams, isNull); expect(state.confidence, .91);
    expect(state.canPreview, isTrue); // MANUAL independent of invalid schedule time
  });
  test('REAL rejects mock/schema mismatch and unwired inventory numbers', () {
    final data = fixture(); data['data_source'] = 'MOCK';
    expect(() => FeederState.decode(jsonEncode(data)), throwsFormatException);
    data['data_source'] = 'REAL'; data['food_reservoir_percent'] = 75;
    expect(() => FeederState.decode(jsonEncode(data)), throwsFormatException);
  });
  test('invalid/stale AI and disabled safety are explicit', () {
    final data = fixture(); (data['ai'] as Map)['health'] = 'STALE';
    (data['safety'] as Map)['servo_armed'] = true;
    final state = FeederState.decode(jsonEncode(data));
    expect(state.classification, 'UNKNOWN'); expect(state.canPreview, isFalse);
  });
  test('receipt only accepts this exact blocked35g request', () {
    final payload = {'request_id': 'synthetic_id', 'sub_source': 'KIOSK', 'target_grams': 35};
    final receipt = PreviewReceipt.decode(preview(payload), 'synthetic_id', 'KIOSK');
    expect(receipt.complete, isTrue); expect(receipt.reason, 'WEIGHT_NOT_CALIBRATED');
    expect(() => PreviewReceipt.decode(preview(payload, unsafe: true), 'synthetic_id', 'KIOSK'), throwsFormatException);
    expect(() => PreviewReceipt.decode(preview(payload), 'other', 'KIOSK'), throwsFormatException);
    expect(() => PreviewReceipt.decode(preview({...payload, 'target_grams': 40}), 'synthetic_id', 'KIOSK'), throwsFormatException);
  });
}
