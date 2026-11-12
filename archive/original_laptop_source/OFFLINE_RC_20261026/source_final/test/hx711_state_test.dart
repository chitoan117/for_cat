import 'dart:convert';

import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/main.dart';
import 'package:feeder_demo/real_backend.dart';
import 'package:feeder_demo/pending_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'state_fixture.dart';

class DiagnosticFixtureBackend extends RealFeederBackend {
  DiagnosticFixtureBackend()
    : super(
        base: Uri.parse('http://fixture.invalid'),
        subSource: 'APP',
        store: MemoryPendingStore(),
      );
  @override
  Future<void> start() async {}
}

Map<String, dynamic> calibratedFixture() {
  final value = fixture();
  value['weight'] = {
    ...value['weight'] as Map<String, dynamic>,
    'grams': 35.02,
    'calibrated': true,
    'calibration_valid': true,
    'calibration_authority': 'JETSON_SQLITE_PHYSICAL_REFERENCE_V1',
    'calibration_state': 'CALIBRATED_PENDING_PERSISTENCE',
    'stable': true,
    'stability_state': 'STABLE',
    'tare_offset_counts': -670000.25,
    'grams_per_count': -.00125,
    'age_seconds': .25,
    'raw_window_samples': 10,
  };
  return value;
}

void main() {
  test(
    'grams require actual validated authority, not a raw count or candidate',
    () {
      final data = calibratedFixture();
      expect(FeederState.decode(jsonEncode(data)).grams, 35.02);
      for (final change in [
        {'calibration_valid': false},
        {'calibration_state': 'CANDIDATE_PENDING_VALIDATION'},
        {'calibration_authority': 'UNKNOWN'},
        {'calibrated': false},
      ]) {
        final copy = {
          ...data,
          'weight': {...data['weight'] as Map<String, dynamic>, ...change},
        };
        expect(FeederState.decode(jsonEncode(copy)).grams, isNull);
      }
    },
  );
  test('signed near-zero, unstable, age and raw metadata remain visible without success claim', () {
    final data = calibratedFixture();
    (data['weight'] as Map<String, dynamic>).addAll({
      'grams': -.03,
      'stable': false,
      'stability_state': 'UNSTABLE',
    });
    final state = FeederState.decode(jsonEncode(data));
    expect(state.grams, -.03);
    expect(state.weightStable, isFalse);
    expect(state.stabilityState, 'UNSTABLE');
    expect(state.rawCounts, isNotNull);
    expect(state.tareCounts, -670000.25);
    expect(state.gramsPerCount, -.00125);
    expect(state.weightAge, .25);
  });
  test('disconnected measurement hides grams and old scale observation', () {
    final data = calibratedFixture();
    (data['esp32'] as Map)['connected'] = false;
    final state = FeederState.decode(jsonEncode(data));
    expect(state.grams, isNull);
    expect(state.tareCounts, isNull);
    expect(state.weightStable, isNull);
  });
  testWidgets('HX diagnostics are in System, not dashboard, at mobile width', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 1100);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final backend = DiagnosticFixtureBackend();
    addTearDown(backend.dispose);
    backend.state = FeederState.decode(jsonEncode(calibratedFixture()));
    await tester.pumpWidget(FeederDemoApp(backend: backend));
    expect(find.textContaining('Tare/offset:'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('nav_3')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('-0.0012500000'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('35.02 g'), findsOneWidget);
    expect(find.text('STABLE'), findsOneWidget);
    expect(find.text('Tare / offset'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
