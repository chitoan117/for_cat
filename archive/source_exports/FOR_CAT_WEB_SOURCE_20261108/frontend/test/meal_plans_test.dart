import 'dart:async';
import 'dart:convert';

import 'package:feeder_demo/meal_plans.dart';
import 'package:feeder_demo/meal_plan_panel.dart';
import 'package:feeder_demo/pending_store.dart';
import 'package:feeder_demo/real_backend.dart';
import 'package:feeder_demo/status_model.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const jsonHeaders = {'content-type': 'application/json'};

Map<String, dynamic> planData({String id = 'plan_fixture', int revision = 1}) =>
    {
      'plan_id': id,
      'revision': revision,
      'name': 'Bữa tối',
      'local_time': '22:50',
      'weekdays': [6],
      'enabled': false,
      'target_grams': 35,
      'timezone': 'Asia/Ho_Chi_Minh',
      'mode': 'SCHEDULED_PREVIEW_ONLY',
      'actuator_execution': false,
    };
String listing(List<Map<String, dynamic>> plans) => jsonEncode({
  'plans': plans,
  'errors': [],
  'mode': 'SCHEDULED_PREVIEW_ONLY',
  'autonomous_worker_enabled': false,
  'actuator_execution': false,
});
RealFeederBackend service(http.Client client) => RealFeederBackend(
  base: Uri.parse('http://fixture.invalid'),
  subSource: 'APP',
  client: client,
  store: MemoryPendingStore(),
  idFactory: () => 'fixture',
  pollInterval: const Duration(milliseconds: 1),
);
Map<String, dynamic> outcome(
  MealPlan plan, {
  bool due = false,
  bool complete = false,
  bool unsafe = false,
}) {
  final id = 'schedule_${List.filled(48, 'a').join()}';
  return {
    'candidate': due,
    'plan_id': plan.id,
    'plan_revision': plan.revision,
    'mode': 'SCHEDULED_PREVIEW_ONLY',
    'clock_source': 'JETSON_SYSTEM_CLOCK',
    'target_grams': 35,
    'actuator_execution': false,
    'actual_dispensed_grams': null,
    'reason': due ? 'DUE_INSTANCE_DRY_RUN' : 'NOT_DUE',
    if (due)
      'request': {
        'request': {
          'request_id': id,
          'source': 'SCHEDULED',
          'sub_source': '',
          'target_grams': 35,
          'actuator_execution': false,
          'actual_dispensed_grams': null,
        },
        'decision': complete
            ? {
                'request_id': id,
                'source': 'SCHEDULED',
                'sub_source': '',
                'target_grams': 35,
                'status': 'DRY_RUN_BLOCKED',
                'reason': 'UNATTENDED_SAFE_MODE',
                'qualification_reason': 'WEIGHT_NOT_CALIBRATED',
                'actuator_execution': unsafe,
                'actual_dispensed_grams': null,
              }
            : null,
      },
  };
}

void main() {
  test(
    'scheduled history retains SCHEDULED label when manual sub-source is empty',
    () async {
      final backend = service(
        MockClient(
          (r) async => http.Response(
            jsonEncode([
              {
                'timestamp': 'fixture-time',
                'kind': 'feed_request_dry_run',
                'details': {
                  'source': 'SCHEDULED',
                  'sub_source': '',
                  'qualification_reason': 'WEIGHT_NOT_CALIBRATED',
                  'request_id': 'schedule_history_fixture',
                  'target_grams': 35,
                  'actuator_execution': false,
                  'actual_dispensed_grams': null,
                },
              },
            ]),
            200,
            headers: jsonHeaders,
          ),
        ),
      );
      addTearDown(backend.dispose);
      await backend.refreshHistory();
      expect(
        backend.activity.single,
        contains('DRY RUN · SCHEDULED · WEIGHT_NOT_CALIBRATED'),
      );
    },
  );
  test('plan decoder rejects wrong target, mode and unsafe schedules', () {
    for (final changes in [
      {'target_grams': 40},
      {'mode': 'AUTO_EXECUTE'},
      {'actuator_execution': true},
      {
        'weekdays': [true],
      },
      {
        'weekdays': [0, 0],
      },
      {'enabled': 1},
      {'local_time': '25:00'},
    ]) {
      expect(
        () => MealPlan.decode({...planData(), ...changes}),
        throwsFormatException,
      );
    }
    expect(MealPlan.decode(planData()).enabled, isFalse);
  });
  test('CRUD requests carry revision and fixed target, refresh real list after mutations', () async {
    final rows = <Map<String, dynamic>>[];
    final writes = <http.Request>[];
    final backend = service(
      MockClient((r) async {
        if (r.method == 'GET') {
          return http.Response(listing(rows), 200, headers: jsonHeaders);
        }
        writes.add(r);
        final p = jsonDecode(r.body) as Map<String, dynamic>;
        if (r.method == 'DELETE') {
          expect(p['expected_revision'], 2);
          rows.clear();
          return http.Response(
            jsonEncode({
              'deleted': true,
              'plan_id': 'plan_fixture',
              'actuator_execution': false,
            }),
            200,
          );
        }
        if (r.method == 'PUT') expect(p['expected_revision'], 1);
        final saved = {...planData(revision: r.method == 'PUT' ? 2 : 1), ...p}
          ..remove('expected_revision');
        rows
          ..clear()
          ..add(saved);
        return http.Response(jsonEncode(saved), 201, headers: jsonHeaders);
      }),
    );
    addTearDown(backend.dispose);
    await backend.saveMealPlan(
      name: 'Bữa sáng',
      localTime: '07:00',
      weekdays: [0],
      enabled: false,
    );
    expect(backend.mealPlans.single.localTime, '07:00');
    await backend.saveMealPlan(
      existing: backend.mealPlans.single,
      name: 'Bữa sáng',
      localTime: '07:30',
      weekdays: [0],
      enabled: true,
    );
    expect(backend.mealPlans.single.revision, 2);
    await backend.deleteMealPlan(backend.mealPlans.single);
    expect(backend.mealPlans, isEmpty);
    expect(writes.map((r) => r.method), ['POST', 'PUT', 'DELETE']);
    expect(writes.where((r) => r.url.path.contains('/feed/')), isEmpty);
  });
  test(
    'lost create reply retains the same configuration ID on explicit retry',
    () async {
      final claims = <String, Map<String, dynamic>>{};
      final ids = <String>[];
      var lost = true;
      final backend = service(
        MockClient((r) async {
          if (r.method == 'GET') {
            return http.Response(
              listing(claims.values.toList()),
              200,
              headers: jsonHeaders,
            );
          }
          final p = jsonDecode(r.body) as Map<String, dynamic>;
          final id = p['plan_id'] as String;
          ids.add(id);
          claims.putIfAbsent(id, () => {...planData(id: id), ...p});
          if (lost) {
            lost = false;
            throw http.ClientException('fixture lost reply after commit');
          }
          return http.Response(
            jsonEncode(claims[id]),
            201,
            headers: jsonHeaders,
          );
        }),
      );
      addTearDown(backend.dispose);
      await backend.saveMealPlan(
        name: 'Lịch',
        localTime: '07:00',
        weekdays: [0],
        enabled: false,
      );
      expect(backend.plansError, isNotNull);
      await backend.saveMealPlan(
        name: 'Lịch',
        localTime: '07:00',
        weekdays: [0],
        enabled: false,
      );
      expect(ids.length, 2);
      expect(ids.toSet().length, 1);
      expect(claims.length, 1);
      expect(backend.mealPlans.length, 1);
    },
  );
  test('old periodic list response cannot overwrite a completed configuration edit', () async {
    final old = Completer<http.Response>();
    var gets = 0;
    final saved = {...planData(), 'name': 'Mới'};
    final backend = service(
      MockClient((r) async {
        if (r.method != 'GET') {
          return http.Response(jsonEncode(saved), 201, headers: jsonHeaders);
        }
        if (++gets == 1) return old.future;
        return http.Response(listing([saved]), 200, headers: jsonHeaders);
      }),
    );
    addTearDown(backend.dispose);
    final pending = backend.refreshMealPlans();
    await backend.saveMealPlan(
      name: 'Mới',
      localTime: '22:50',
      weekdays: [6],
      enabled: false,
    );
    old.complete(http.Response(listing([]), 200));
    await pending;
    expect(backend.mealPlans.single.name, 'Mới');
  });
  test('future preview never polls or claims dispensing; double invocation is locked', () async {
    final reply = Completer<http.Response>();
    final plan = MealPlan.decode(planData());
    var posts = 0;
    final backend = service(
      MockClient((r) async {
        posts++;
        return reply.future;
      }),
    );
    addTearDown(backend.dispose);
    final first = backend.previewMealPlan(plan);
    await backend.previewMealPlan(plan);
    await Future<void>.delayed(Duration.zero);
    expect(posts, 1);
    reply.complete(http.Response(jsonEncode(outcome(plan)), 200));
    await first;
    expect(backend.schedulePreview!.reason, 'NOT_DUE');
    expect(backend.scheduledReceipt, isNull);
    expect(backend.receipt, isNull);
  });
  test(
    'due preview polls the same SCHEDULED ID and validates blocked decision',
    () async {
      final plan = MealPlan.decode(planData());
      final calls = <http.Request>[];
      final backend = service(
        MockClient((r) async {
          calls.add(r);
          if (r.method == 'POST') {
            return http.Response(jsonEncode(outcome(plan, due: true)), 200);
          }
          if (r.url.path.contains('/api/feed/preview/')) {
            return http.Response(
              jsonEncode(outcome(plan, due: true, complete: true)['request']),
              200,
            );
          }
          return http.Response('[]', 200);
        }),
      );
      addTearDown(backend.dispose);
      await backend.previewMealPlan(plan);
      expect(backend.scheduledReceipt!.complete, isTrue);
      expect(backend.scheduledReceipt!.reason, 'WEIGHT_NOT_CALIBRATED');
      expect(backend.scheduledReceipt!.request['source'], 'SCHEDULED');
      expect(backend.receipt, isNull);
      expect(calls.where((r) => r.method == 'POST').length, 1);
      expect(
        calls
            .singleWhere((r) => r.url.path.contains('/api/feed/preview/'))
            .url
            .path
            .endsWith(backend.scheduledReceipt!.id),
        isTrue,
      );
    },
  );
  test(
    'unsafe scheduled result becomes error, never a physical success',
    () async {
      final plan = MealPlan.decode(planData());
      final backend = service(
        MockClient(
          (r) async => http.Response(
            jsonEncode(outcome(plan, due: true, complete: true, unsafe: true)),
            200,
          ),
        ),
      );
      addTearDown(backend.dispose);
      await backend.previewMealPlan(plan);
      expect(backend.plansError, isNotNull);
      expect(backend.scheduledReceipt, isNull);
    },
  );
  testWidgets('mobile plan editor validates time and saves new plan disabled', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final rows = <Map<String, dynamic>>[];
    var posts = 0;
    final backend = service(
      MockClient((r) async {
        if (r.method == 'GET') {
          return http.Response(listing(rows), 200, headers: jsonHeaders);
        }
        posts++;
        final body = jsonDecode(r.body) as Map<String, dynamic>;
        expect(body['enabled'], isFalse);
        expect(body['target_grams'], 35);
        rows.add({...planData(), ...body});
        return http.Response(
          jsonEncode(rows.single),
          201,
          headers: jsonHeaders,
        );
      }),
    );
    addTearDown(backend.dispose);
    backend.connectionStatus = AppStatus.online;
    await backend.refreshMealPlans();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AnimatedBuilder(
              animation: backend,
              builder: (_, _) => MealPlanPanel(backend: backend),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Thêm lịch'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Bữa sáng');
    await tester.enterText(find.byType(TextFormField).at(1), '25:90');
    await tester.tap(find.text('Lưu lịch'));
    await tester.pumpAndSettle();
    expect(posts, 0);
    expect(find.text('Nhập giờ từ 00:00 đến 23:59'), findsOneWidget);
    await tester.enterText(find.byType(TextFormField).at(1), '07:30');
    await tester.tap(find.text('Lưu lịch'));
    await tester.pumpAndSettle();
    expect(posts, 1);
    expect(backend.mealPlans.single.localTime, '07:30');
    expect(find.textContaining('Đang tắt'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
