import 'dart:convert';

import 'package:feeder_demo/meal_plans.dart';
import 'package:feeder_demo/meal_plan_panel.dart';
import 'package:feeder_demo/real_backend.dart';
import 'package:feeder_demo/pending_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

Map<String, dynamic> workerData() => {
  'enabled': true,
  'running': true,
  'status': 'RUNNING',
  'mode': 'DRY_RUN_ONLY',
  'timezone': 'Asia/Ho_Chi_Minh',
  'target_grams': 35,
  'auto_feed': false,
  'auto_water': false,
  'actuator_execution': false,
  'actual_dispensed_grams': null,
  'poll_count': 7,
  'submitted_count': 1,
  'duplicate_observations': 6,
  'error_count': 0,
  'last_poll_at': '2026-10-26T02:30:10+00:00',
  'last_error': null,
};
Map<String, dynamic> occurrence() => {
  'occurrence_id': 'occurrence_fixture',
  'request_id': 'schedule_fixture',
  'plan_id': 'plan_fixture',
  'local_date': '2026-10-26',
  'origin': 'WORKER',
  'target_grams': 35,
  'actuator_execution': false,
  'actual_dispensed_grams': null,
  'decision': {
    'request_id': 'schedule_fixture',
    'source': 'SCHEDULED',
    'target_grams': 35,
    'status': 'DRY_RUN_BLOCKED',
    'actuator_execution': false,
    'actual_dispensed_grams': null,
    'qualification_reason': 'WEIGHT_NOT_CALIBRATED',
  },
};
void main() {
  test('unknown worker is unknown, not a fabricated running worker', () {
    final state = ScheduledWorkerStatus.unknown();
    expect(state.status, 'UNKNOWN');
    expect(state.enabled, isNull);
    expect(state.data['submitted_count'], isNull);
  });
  test('worker decode accepts autonomous DRY RUN only', () {
    expect(ScheduledWorkerStatus.decode(workerData()).enabled, isTrue);
    for (final change in [
      {'mode': 'PHYSICAL'},
      {'auto_feed': true},
      {'auto_water': true},
      {'actuator_execution': true},
      {'target_grams': 40},
      {'poll_count': -1},
      {'enabled': false},
      {'running': 'yes'},
    ]) {
      expect(
        () => ScheduledWorkerStatus.decode({...workerData(), ...change}),
        throwsFormatException,
      );
    }
  });
  test('occurrence history cannot claim a physical completed feed', () {
    expect(decodeOccurrences([occurrence()]).single['origin'], 'WORKER');
    expect(
      () => decodeOccurrences([
        {...occurrence(), 'actuator_execution': true},
      ]),
      throwsFormatException,
    );
    expect(
      () => decodeOccurrences([
        {
          ...occurrence(),
          'decision': {
            ...occurrence()['decision'] as Map<String, dynamic>,
            'actual_dispensed_grams': 35,
          },
        },
      ]),
      throwsFormatException,
    );
  });
  test('real list accepts new worker mode; failed refresh clears healthy worker state', () async {
    var fail = false;
    final calls = <String>[];
    final backend = RealFeederBackend(
      base: Uri.parse('http://fixture.invalid'),
      subSource: 'APP',
      store: MemoryPendingStore(),
      client: MockClient((r) async {
        calls.add(r.method);
        if (fail) throw http.ClientException('fixture offline');
        return http.Response(
          jsonEncode({
            'plans': [],
            'errors': [],
            'mode': 'SCHEDULED_DRY_RUN',
            'autonomous_worker_enabled': true,
            'worker': workerData(),
            'recent_occurrences': [occurrence()],
            'actuator_execution': false,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );
    addTearDown(backend.dispose);
    await backend.refreshMealPlans();
    expect(backend.scheduledWorker.status, 'RUNNING');
    expect(backend.scheduledOccurrences.length, 1);
    fail = true;
    await backend.refreshMealPlans();
    expect(backend.scheduledWorker.status, 'UNKNOWN');
    expect(backend.scheduledOccurrences, isEmpty);
    expect(backend.plansError, isNotNull);
    expect(calls.every((m) => m == 'GET'), isTrue);
  });
  testWidgets(
    'mobile panel shows real worker and automatic occurrence, not completed feeding',
    (tester) async {
      tester.view.physicalSize = const Size(390, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final backend = RealFeederBackend(
        base: Uri.parse('http://fixture.invalid'),
        subSource: 'APP',
        store: MemoryPendingStore(),
      );
      addTearDown(backend.dispose);
      backend.scheduledWorker = ScheduledWorkerStatus.decode(workerData());
      backend.scheduledOccurrences.addAll(decodeOccurrences([occurrence()]));
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(child: MealPlanPanel(backend: backend)),
          ),
        ),
      );
      expect(find.text('Scheduled Worker · RUNNING'), findsNothing);
      await tester.tap(find.text('Chi tiết kỹ thuật'));
      await tester.pumpAndSettle();
      expect(find.text('Scheduled Worker · RUNNING'), findsOneWidget);
      expect(find.textContaining('Tự động'), findsOneWidget);
      expect(find.text('Cân chưa hiệu chuẩn'), findsOneWidget);
      expect(
        find.textContaining('actual_dispensed_grams=null'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
