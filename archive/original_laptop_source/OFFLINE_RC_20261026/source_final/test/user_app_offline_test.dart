import 'dart:async';
import 'dart:convert';

import 'package:feeder_demo/diagnostic_models.dart';
import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/history_model.dart';
import 'package:feeder_demo/main.dart';
import 'package:feeder_demo/meal_plans.dart';
import 'package:feeder_demo/mock_backend.dart';
import 'package:feeder_demo/pending_store.dart';
import 'package:feeder_demo/real_backend.dart';
import 'package:feeder_demo/status_model.dart';
import 'package:feeder_demo/ui_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'state_fixture.dart';
import 'scheduled_worker_test.dart' show workerData, occurrence;

http.Response jsonResponse(Object body) => http.Response(
  jsonEncode(body),
  200,
  headers: {'content-type': 'application/json'},
);

class StaticRealBackend extends RealFeederBackend {
  StaticRealBackend()
    : super(
        base: Uri.parse('http://offline.fixture.invalid'),
        subSource: 'APP',
        store: MemoryPendingStore(),
      );
  @override
  Future<void> start() async {}
}

class EmptySocket implements StateSocket {
  final controller = StreamController<dynamic>.broadcast();
  @override
  Stream<dynamic> get stream => controller.stream;
  @override
  Future<void> get ready async {}
  @override
  Future<void> close() => controller.close();
}

Map<String, dynamic> occurrenceListing() => {
  'plans': [],
  'errors': [],
  'mode': 'SCHEDULED_DRY_RUN',
  'autonomous_worker_enabled': true,
  'worker': workerData(),
  'recent_occurrences': [
    {...occurrence(), 'created_at': '2026-10-26T02:20:01+00:00'},
  ],
  'actuator_execution': false,
};

void main() {
  test('sensor-specific stale and unwired states hide even contradictory distances', () {
    final data = fixture();
    (data['approach'] as Map)['stale'] = true;
    (data['approach'] as Map)['timeout'] = false;
    var sensor = UltrasonicState.fromSystem(
      FeederState.decode(jsonEncode(data)),
    ).first;
    expect(sensor.state, AppStatus.stale);
    expect(sensor.distanceCm, isNull);
    (data['approach'] as Map)['stale'] = false;
    (data['approach'] as Map)['wired'] = false;
    sensor = UltrasonicState.fromSystem(FeederState.decode(jsonEncode(data)))
        .first;
    expect(sensor.state, AppStatus.notWired);
    expect(sensor.distanceCm, isNull);
    data['approach'] = {
      'configured': true,
      'health': 'NOT_CONNECTED',
      'valid': false,
    };
    sensor = UltrasonicState.fromSystem(FeederState.decode(jsonEncode(data)))
        .first;
    expect(sensor.state, AppStatus.unknown);
    expect(sensor.timeout, isNull);
  });
  test('dedicated AUTO_CAT state is not live when ESP32 or AI is stale', () {
    final data = fixture();
    data['auto_cat'] = {
      'state': 'READY_TO_REQUEST',
      'checks': {'ai': true, 'distance': true},
    };
    (data['esp32'] as Map)['health'] = 'ESP32_STALE';
    var view = AutoCatView.fromSystem(FeederState.decode(jsonEncode(data)));
    expect(view.state, 'UNKNOWN');
    expect(view.checks.values, everyElement(isNull));
    (data['esp32'] as Map)['health'] = 'ESP32_CONNECTED';
    (data['ai'] as Map)['health'] = 'STALE';
    view = AutoCatView.fromSystem(FeederState.decode(jsonEncode(data)));
    expect(view.state, 'UNKNOWN');
    expect(view.checks['ai'], isNull);
  });
  test(
    'calibration GET-only 404 and invalid payload remain unsupported/unknown',
    () async {
      final requests = <http.Request>[];
      var unsupported = true;
      final b = RealFeederBackend(
        base: Uri.parse('http://fixture.invalid'),
        subSource: 'APP',
        store: MemoryPendingStore(),
        client: MockClient((r) async {
          requests.add(r);
          return unsupported
              ? http.Response('', 404)
              : jsonResponse({
                  'actuator_execution': true,
                  'actual_dispensed_grams': 35,
                });
        }),
      );
      addTearDown(b.dispose);
      await b.refreshCalibration();
      expect(b.calibrationSupported, isFalse);
      expect(b.calibrationInfo, isNull);
      unsupported = false;
      await b.refreshCalibration();
      expect(b.calibrationSupported, isNull);
      expect(b.calibrationError, isNotNull);
      expect(
        requests.every(
          (r) => r.method == 'GET' && r.url.path == '/api/hx711/calibration',
        ),
        isTrue,
      );
    },
  );
  testWidgets(
    'long technical IDs are available in full after expansion at 320px',
    (tester) async {
      tester.view.physicalSize = const Size(320, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final identifier = List.filled(64, 'a').join();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView(
              children: [
                TechnicalDetails(
                  data: {
                    'request_id': identifier,
                    'occurrence_id': 'schedule_$identifier',
                  },
                ),
              ],
            ),
          ),
        ),
      );
      await tester.tap(find.text('Chi tiết kỹ thuật'));
      await tester.pumpAndSettle();
      expect(find.textContaining('schedule_$identifier'), findsOneWidget);
      expect(find.text('Sao chép chi tiết'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  test('P0 states distinguish wiring/config/timeout/stale/offline/missing', () {
    expect(parseStatus('NOT_WIRED'), AppStatus.notWired);
    expect(parseStatus('NOT_CONFIGURED'), AppStatus.notConfigured);
    final data = fixture();
    data['approach'] = {
      'health': 'NOT_CONNECTED',
      'valid': false,
      'distance_cm': null,
      'timeout_count': 3,
    };
    final sensors = UltrasonicState.fromSystem(
      FeederState.decode(jsonEncode(data)),
    );
    expect(sensors.first.state, AppStatus.timeout);
    expect(sensors.first.distanceCm, isNull);
    expect(sensors[1].wired, isFalse);
    expect(sensors[1].state, AppStatus.notWired);
    expect(sensors[1].triggerGpio, isNull);
    expect(sensors[1].proposedTrigger, 16);
    (data['esp32'] as Map)['health'] = 'ESP32_STALE';
    expect(
      UltrasonicState.fromSystem(FeederState.decode(jsonEncode(data)))
          .first
          .state,
      AppStatus.stale,
    );
    expect(
      UltrasonicState.fromSystem(FeederState.unknown()).first.state,
      AppStatus.unknown,
    );
  });
  test('P0 actual dispensed never comes from weight.grams or target', () {
    final data = fixture();
    (data['weight'] as Map)['grams'] = 35;
    expect(FeederState.decode(jsonEncode(data)).actualDispensedGrams, isNull);
    (data['feed'] as Map)['actual_dispensed_grams'] = 35.4;
    expect(FeederState.decode(jsonEncode(data)).actualDispensedGrams, isNull);
    (data['feed'] as Map)['actuator_execution'] = true;
    expect(FeederState.decode(jsonEncode(data)).actualDispensedGrams, 35.4);
    (data['feed'] as Map)['dry_run'] = true;
    expect(FeederState.decode(jsonEncode(data)).actualDispensedGrams, isNull);
  });
  test('persisted scheduled occurrences populate history even when event ring is empty', () async {
    final b = RealFeederBackend(
      base: Uri.parse('http://fixture.invalid'),
      subSource: 'APP',
      store: MemoryPendingStore(),
      client: MockClient(
        (r) async => r.url.path == '/api/meal-plans'
            ? jsonResponse(occurrenceListing())
            : jsonResponse([]),
      ),
    );
    addTearDown(b.dispose);
    await b.refreshMealPlans();
    await b.refreshHistory();
    expect(b.historyRecords.length, 1);
    expect(b.historyRecords.single.source, 'SCHEDULED');
    expect(b.historyRecords.single.status, AppStatus.blocked);
    expect(b.historyRecords.single.provenance, 'scheduled_occurrences');
    expect(b.activity.single, contains('DRY RUN · SCHEDULED'));
  });
  test('history deduplicates native event and occurrence by canonical request identity', () {
    final row = {...occurrence(), 'created_at': '2026-10-26T02:20:01+00:00'};
    final fromDb = HistoryEntry.fromOccurrence(row)!;
    final native = HistoryEntry.fromEvent({
      'seq': 8,
      'kind': 'feed_request_dry_run',
      'timestamp': '2026-10-26T02:20:02+00:00',
      'details': row['decision'],
    })!;
    final result = mergeHistory([native], [fromDb], []);
    expect(result.length, 1);
    expect(result.single.provenance, 'scheduled_occurrences');
    expect(result.single.title, 'Lịch ăn tự động');
  });
  test('invalid or physical-success payload is not presented as dry-run completion', () {
    final data = {
      ...occurrence(),
      'decision': {
        ...occurrence()['decision'] as Map<String, dynamic>,
        'actuator_execution': true,
        'actual_dispensed_grams': 35,
      },
    };
    expect(HistoryEntry.fromOccurrence(data), isNull);
    expect(
      HistoryEntry.fromEvent({'kind': 'telemetry_sample', 'details': {}}),
      isNull,
    );
  });
  test(
    'AUTO_CAT explicit state only; missing dedicated state stays unknown',
    () {
      final data = fixture();
      (data['ai'] as Map)['classification'] = 'CAT';
      var view = AutoCatView.fromSystem(FeederState.decode(jsonEncode(data)));
      expect(view.state, 'UNKNOWN');
      expect(view.supported, isFalse);
      expect(view.checks['ai'], isTrue);
      expect(view.checks['cooldown'], isNull);
      data['auto_cat'] = {
        'state': 'BLOCKED',
        'checks': {
          'ai': true,
          'distance': true,
          'stable': false,
          'cooldown': true,
          'hx711': false,
        },
      };
      view = AutoCatView.fromSystem(FeederState.decode(jsonEncode(data)));
      expect(view.state, 'BLOCKED');
      expect(view.checks['stable'], isFalse);
    },
  );
  test(
    'next meal uses Vietnam day, enabled plans and persisted occurrence dedupe',
    () {
      final p = MealPlan(
        id: 'meal',
        name: 'test',
        localTime: '07:00',
        revision: 1,
        weekdays: const [0, 1, 2, 3, 4, 5, 6],
        enabled: true,
      );
      final now = DateTime.parse('2026-10-26T00:00:05Z');
      expect(
        nextMeal([p], now, [])!.dueUtc,
        DateTime.parse('2026-10-26T00:00:00Z'),
      );
      expect(
        nextMeal(
          [p],
          now,
          [
            {'plan_id': 'meal', 'local_date': '2026-10-26'},
          ],
        )!.dueUtc,
        DateTime.parse('2026-10-27T00:00:00Z'),
      );
    },
  );
  test(
    'REAL failed backend remains offline/unknown without fixtures',
    () async {
      final b = RealFeederBackend(
        base: Uri.parse('http://fixture.invalid'),
        subSource: 'APP',
        store: MemoryPendingStore(),
        socketFactory: (_) => EmptySocket(),
        client: MockClient(
          (r) async => throw http.ClientException('fixture offline'),
        ),
      );
      addTearDown(b.dispose);
      await b.start();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(b.isMock, isFalse);
      expect(b.connectionStatus, AppStatus.offline);
      expect(b.state.linkHealth, 'UNKNOWN');
      expect(b.state.rawCounts, isNull);
      expect(b.state.inventory('food'), isNull);
      expect(b.historyRecords, isEmpty);
    },
  );
  testWidgets('overview is user view, target wording clear and no raw fields', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final b = StaticRealBackend();
    addTearDown(b.dispose);
    b.state = FeederState.decode(jsonEncode(fixture()));
    b.connectionStatus = AppStatus.online;
    await tester.pumpWidget(FeederDemoApp(backend: b));
    await tester.scrollUntilVisible(find.text('Mục tiêu mỗi lần: 35 g'), 200);
    expect(find.text('Kết quả cấp: Chưa xác minh'), findsOneWidget);
    expect(find.textContaining('35 g thực cấp'), findsNothing);
    expect(find.textContaining('HX711 raw:'), findsNothing);
    expect(find.textContaining('Tare/offset:'), findsNothing);
  });
  testWidgets('physical value only displayed when real field supplied', (
    tester,
  ) async {
    final b = StaticRealBackend();
    addTearDown(b.dispose);
    final data = fixture();
    (data['feed'] as Map)['actual_dispensed_grams'] = 35.4;
    (data['feed'] as Map)['actuator_execution'] = true;
    b.state = FeederState.decode(jsonEncode(data));
    b.connectionStatus = AppStatus.online;
    await tester.pumpWidget(FeederDemoApp(backend: b));
    await tester.scrollUntilVisible(find.text('Thực cấp: 35.4 g'), 200);
    expect(find.text('Thực cấp: 35.4 g'), findsOneWidget);
  });
  testWidgets(
    'history shows real occurrence and unsupported filters explicitly',
    (tester) async {
      final b = StaticRealBackend();
      addTearDown(b.dispose);
      b.historyLoaded = true;
      b.connectionStatus = AppStatus.online;
      b.historyRecords.add(
        HistoryEntry.fromOccurrence({
          ...occurrence(),
          'created_at': '2026-10-26T02:20:01Z',
        })!,
      );
      await tester.pumpWidget(FeederDemoApp(backend: b));
      await tester.tap(find.byKey(const ValueKey('nav_2')));
      await tester.pumpAndSettle();
      expect(find.text('Lịch ăn tự động'), findsOneWidget);
      expect(find.textContaining('Cân chưa hiệu chuẩn'), findsOneWidget);
      expect(find.textContaining('Hoàn tất cấp thức ăn'), findsNothing);
      await tester.tap(find.widgetWithText(ChoiceChip, 'Nước'));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Chưa hỗ trợ nhật ký cấp nước'),
        findsOneWidget,
      );
    },
  );
  testWidgets(
    'calibration UI is read-only with disabled actions and explicit unknown AUTO_CAT',
    (tester) async {
      tester.view.physicalSize = const Size(390, 1100);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final b = StaticRealBackend();
      addTearDown(b.dispose);
      b.state = FeederState.decode(jsonEncode(fixture()));
      b.connectionStatus = AppStatus.online;
      await tester.pumpWidget(FeederDemoApp(backend: b));
      await tester.tap(find.byKey(const ValueKey('nav_3')));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Hiệu chuẩn cân'),
        250,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Hiệu chuẩn cân'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Bắt đầu hiệu chuẩn — Chưa khả dụng'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      final button = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'Bắt đầu hiệu chuẩn — Chưa khả dụng'),
      );
      expect(button.onPressed, isNull);
      expect(find.textContaining('0 g — Tare'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('AUTO CAT'),
        500,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Backend chưa expose state AUTO_CAT riêng'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
  for (final width in [320.0, 390.0, 768.0, 1280.0]) {
    testWidgets(
      'P1 responsive all five tabs at width $width, MOCK badge stays visible',
      (tester) async {
        tester.view.physicalSize = Size(width, 1000);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.reset);
        final b = MockFeederBackend();
        addTearDown(b.dispose);
        await tester.pumpWidget(FeederDemoApp(backend: b));
        for (var tab = 0; tab < 5; tab++) {
          await tester.tap(find.byKey(ValueKey('nav_$tab')));
          await tester.pumpAndSettle();
          expect(
            find.textContaining('MOCK · Dữ liệu kiểm thử'),
            findsOneWidget,
          );
          expect(tester.takeException(), isNull);
        }
        await tester.scrollUntilVisible(
          find.text('AUTO_WATER'),
          300,
          scrollable: find.byType(Scrollable).first,
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
    );
  }
}
