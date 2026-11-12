import 'dart:convert';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'meal_plans.dart';
import 'history_model.dart';
import 'status_model.dart';
export 'feeder_backend.dart' show DemoScenario;

/// Explicit dev fixtures only. Nothing in REAL factory/reconnect falls back here.
class MockFeederBackend extends FeederBackend {
  DemoScenario scenario = DemoScenario.normal;
  MockFeederBackend({DemoScenario initial = DemoScenario.normal}) {
    setScenario(initial);
  }
  @override
  bool get isMock => true;
  @override
  String get endpoint => 'MOCK · offline fixture';
  void setScenario(DemoScenario value) {
    scenario = value;
    final online = value != DemoScenario.offline && value != DemoScenario.stale;
    final stale = value == DemoScenario.stale,
        timeout = value == DemoScenario.ultrasonicTimeout;
    final calibrated = value == DemoScenario.hxCalibrated;
    connectionStatus = stale ? AppStatus.stale : AppStatus.online;
    final fixture = {
      'schema_version': 'system_state_v1',
      'data_source': 'MOCK',
      'observed_at': '2026-10-26T02:00:00+00:00',
      'time': {'time_valid': true, 'source': 'MOCK_CLOCK'},
      'esp32': {
        'connected': online,
        'health': stale
            ? 'ESP32_STALE'
            : online
            ? 'ESP32_CONNECTED'
            : 'ESP32_DISCONNECTED',
        'stale': stale,
      },
      'ai': {
        'classification': value == DemoScenario.ownerCat
            ? 'CAT'
            : value == DemoScenario.dog
            ? 'DOG'
            : 'NONE',
        'health': online ? 'ONLINE' : 'DISCONNECTED',
        'confidence': value == DemoScenario.ownerCat ? .94 : null,
        'source': 'MOCK_FIXTURE',
      },
      'food_reservoir_sensor': 'MOCK',
      'food_reservoir_percent': value == DemoScenario.foodEmpty ? 0 : 75,
      'water_reservoir_sensor': 'MOCK',
      'water_reservoir_percent': value == DemoScenario.waterLow ? 12 : 82,
      'approach': {
        'distance_cm': timeout ? null : 24.8,
        'valid': !timeout,
        'health': timeout ? 'NOT_CONNECTED' : 'NOT_CALIBRATED',
        'timeout_count': timeout ? 3 : 0,
      },
      'water_operational': {
        'distance_cm': 25.9,
        'valid': true,
        'health': 'NOT_CALIBRATED',
        'timeout_count': 0,
      },
      'weight': {
        'raw_counts': -671373,
        'raw_available': true,
        'calibrated': calibrated,
        'calibration_valid': calibrated,
        'grams': calibrated ? 35.02 : null,
        'calibration_authority': 'JETSON_SQLITE_PHYSICAL_REFERENCE_V1',
        'calibration_state': calibrated ? 'CALIBRATED' : 'NOT_CALIBRATED',
        'health': calibrated ? 'HEALTHY' : 'NOT_CALIBRATED',
        'stability_state': calibrated ? 'STABLE' : 'NOT_CALIBRATED',
        'stable': calibrated ? true : null,
        'raw_window_samples': 10,
        'tare_offset_counts': calibrated ? -670000.25 : null,
        'grams_per_count': calibrated ? -.00125 : null,
        'age_seconds': .25,
      },
      'oled': {'health': 'HEALTHY'},
      'manual_button': {
        'health': 'HEALTHY',
        'pressed': false,
        'request_count': 2,
      },
      'feed': {
        'target_grams': 35,
        'actuator_execution': false,
        'actual_dispensed_grams': null,
      },
      'safety': {
        'servo_armed': false,
        'pump_armed': false,
        'auto_feed': false,
        'auto_water': false,
        'actuator_outputs_enabled': 0,
        'actuator_execution': false,
      },
      'decisions': {
        'near_configured': false,
        'near_stable': false,
        'near_threshold_cm': null,
        'mode': 'DRY_RUN_ONLY',
      },
    };
    state = FeederState.decode(jsonEncode(fixture), allowMock: true);
    plansLoaded = true;
    historyLoaded = true;
    mealPlans
      ..clear()
      ..addAll([
        for (final hour in ['07:00', '12:00', '18:00'])
          MealPlan(
            id: 'mock_${hour.replaceAll(':', '')}',
            name: 'Lịch MOCK',
            localTime: hour,
            revision: 1,
            weekdays: const [0, 1, 2, 3, 4, 5, 6],
            enabled: true,
          ),
      ]);
    scheduledWorker = ScheduledWorkerStatus.decode({
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
      'last_poll_at': '2026-10-26T02:00:00+00:00',
      'last_error': null,
    });
    final row = {
      'occurrence_id': 'occurrence_mock_fixture',
      'request_id': 'schedule_mock_fixture',
      'plan_id': 'mock_0700',
      'local_date': '2026-10-26',
      'created_at': '2026-10-26T00:00:01+00:00',
      'origin': 'WORKER',
      'target_grams': 35,
      'actuator_execution': false,
      'actual_dispensed_grams': null,
      'decision': {
        'request_id': 'schedule_mock_fixture',
        'source': 'SCHEDULED',
        'target_grams': 35,
        'status': 'DRY_RUN_BLOCKED',
        'reason': 'UNATTENDED_SAFE_MODE',
        'qualification_reason': 'WEIGHT_NOT_CALIBRATED',
        'actuator_execution': false,
        'actual_dispensed_grams': null,
      },
    };
    scheduledOccurrences
      ..clear()
      ..addAll(decodeOccurrences([row]));
    historyRecords
      ..clear()
      ..addAll([
        HistoryEntry.fromOccurrence(row)!,
        HistoryEntry.fromEvent({
          'seq': 2,
          'kind': 'feed_request_dry_run',
          'timestamp': '2026-10-26T00:20:00+00:00',
          'details': {
            'request_id': 'manual_mock_fixture',
            'source': 'MANUAL',
            'sub_source': 'APP',
            'target_grams': 35,
            'status': 'DRY_RUN_BLOCKED',
            'reason': 'UNATTENDED_SAFE_MODE',
            'qualification_reason': 'WEIGHT_NOT_CALIBRATED',
            'actuator_execution': false,
            'actual_dispensed_grams': null,
          },
        })!,
        HistoryEntry.fromEvent({
          'seq': 3,
          'kind': 'ai_transition',
          'timestamp': '2026-10-26T00:30:00+00:00',
          'details': {'classification': 'CAT'},
        })!,
        HistoryEntry.fromEvent({
          'seq': 4,
          'kind': 'serial_connected',
          'timestamp': '2026-10-26T00:35:00+00:00',
          'details': {'health': 'ESP32_CONNECTED'},
        })!,
      ]);
    historyRecords.sort((a, b) => (b.timestamp!).compareTo(a.timestamp!));
    activity
      ..clear()
      ..addAll(historyRecords.map((e) => e.legacyText));
    calibrationInfo = {
      'active': null,
      'latest_session': {'state': 'AWAITING_ZERO'},
      'point_summaries': [],
      'actuator_execution': false,
      'actual_dispensed_grams': null,
    };
    calibrationSupported = true;
    notifyListeners();
  }

  @override
  Future<void> start() async {}
  @override
  Future<void> refreshHistory() async {}
  @override
  Future<void> feed() async {
    if (!canFeed) return;
    feeding = true;
    notifyListeners();
    await Future<void>.delayed(const Duration(milliseconds: 100));
    feeding = false;
    scenario = DemoScenario.success;
    activity.insert(0, 'MOCK · request DRY RUN 35 g · không cấp thức ăn');
    notifyListeners();
  }
}
