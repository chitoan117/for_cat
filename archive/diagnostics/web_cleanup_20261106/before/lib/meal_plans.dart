import 'dart:convert';

import 'feeder_state.dart';

bool scheduleMode(Object? value) =>
    ['SCHEDULED_PREVIEW_ONLY', 'SCHEDULED_DRY_RUN'].contains(value);

class ScheduledWorkerStatus {
  final Map<String, dynamic> data;
  const ScheduledWorkerStatus._(this.data);
  factory ScheduledWorkerStatus.unknown() =>
      const ScheduledWorkerStatus._({'status': 'UNKNOWN'});
  factory ScheduledWorkerStatus.decode(Object? raw) {
    final data = object(raw);
    if (data['enabled'] is! bool ||
        data['running'] is! bool ||
        data['mode'] != 'DRY_RUN_ONLY' ||
        data['timezone'] != 'Asia/Ho_Chi_Minh' ||
        data['target_grams'] != 35 ||
        data['auto_feed'] != false ||
        data['auto_water'] != false ||
        data['actuator_execution'] != false ||
        data['actual_dispensed_grams'] != null ||
        ![
          'DISABLED',
          'STARTING',
          'RUNNING',
          'DEGRADED',
          'WAITING_TIME_VALID',
          'WAITING_ESP32',
          'WAITING_SAFE_STATE',
          'STALE',
          'STOPPED',
        ].contains(data['status'])) {
      throw const FormatException('Invalid Scheduled Worker state');
    }
    for (final key in [
      'poll_count',
      'submitted_count',
      'duplicate_observations',
      'error_count',
    ]) {
      if (data[key] is! int || (data[key] as int) < 0) {
        throw const FormatException('Invalid worker counter');
      }
    }
    if (data['enabled'] == false && data['running'] == true) {
      throw const FormatException('Disabled worker running');
    }
    return ScheduledWorkerStatus._(data);
  }
  bool? get enabled => data['enabled'] is bool ? data['enabled'] as bool : null;
  String get status => text(data['status']);
}

List<Map<String, dynamic>> decodeOccurrences(Object? raw) {
  if (raw == null) return [];
  if (raw is! List || raw.length > 20) {
    throw const FormatException('Invalid occurrence history');
  }
  return raw.map((dynamic item) {
    final row = object(item);
    if (row['occurrence_id'] is! String ||
        row['request_id'] is! String ||
        row['plan_id'] is! String ||
        !['WORKER', 'PREVIEW'].contains(row['origin']) ||
        row['target_grams'] != 35 ||
        row['actuator_execution'] != false ||
        row['actual_dispensed_grams'] != null) {
      throw const FormatException('Invalid occurrence');
    }
    if (row['decision'] != null) {
      final d = object(row['decision']);
      if (d['request_id'] != row['request_id'] ||
          d['source'] != 'SCHEDULED' ||
          d['target_grams'] != 35 ||
          d['status'] != 'DRY_RUN_BLOCKED' ||
          d['actuator_execution'] != false ||
          d['actual_dispensed_grams'] != null) {
        throw const FormatException('Unsafe occurrence decision');
      }
    }
    return Map<String, dynamic>.unmodifiable(row);
  }).toList();
}

class MealPlan {
  final String id, name, localTime;
  final int revision;
  final List<int> weekdays;
  final bool enabled;
  const MealPlan({
    required this.id,
    required this.name,
    required this.localTime,
    required this.revision,
    required this.weekdays,
    required this.enabled,
  });

  factory MealPlan.decode(Object? raw) {
    final data = object(raw);
    final id = data['plan_id'], name = data['name'], time = data['local_time'];
    final revision = data['revision'], days = data['weekdays'];
    if (id is! String ||
        !RegExp(r'^[A-Za-z0-9_-]{1,64}$').hasMatch(id) ||
        name is! String ||
        name.trim().isEmpty ||
        name.length > 64 ||
        time is! String ||
        !RegExp(r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$').hasMatch(time) ||
        revision is! int ||
        revision < 1 ||
        days is! List ||
        days.isEmpty ||
        days.length > 7 ||
        days.any((dynamic d) => d is! int || d < 0 || d > 6) ||
        days.toSet().length != days.length ||
        data['enabled'] is! bool ||
        data['target_grams'] != 35 ||
        data['timezone'] != 'Asia/Ho_Chi_Minh' ||
        !scheduleMode(data['mode']) ||
        data['actuator_execution'] != false) {
      throw const FormatException('Invalid Meal Plan');
    }
    return MealPlan(
      id: id,
      name: name,
      localTime: time,
      revision: revision,
      weekdays: List<int>.unmodifiable(days.cast<int>()),
      enabled: data['enabled'] as bool,
    );
  }

  Map<String, dynamic> get definition => {
    'name': name,
    'local_time': localTime,
    'weekdays': weekdays,
    'enabled': enabled,
    'target_grams': 35,
    'timezone': 'Asia/Ho_Chi_Minh',
  };
}

class SchedulePreview {
  final Map<String, dynamic> data;
  final PreviewReceipt? receipt;
  const SchedulePreview._(this.data, this.receipt);
  factory SchedulePreview.decode(String body, MealPlan plan) {
    if (body.length > 32768) throw const FormatException('Preview too large');
    final data = object(jsonDecode(body));
    if (data['plan_id'] != plan.id ||
        data['plan_revision'] != plan.revision ||
        !scheduleMode(data['mode']) ||
        data['target_grams'] != 35 ||
        data['actuator_execution'] != false ||
        data['actual_dispensed_grams'] != null ||
        data['clock_source'] != 'JETSON_SYSTEM_CLOCK' ||
        data['candidate'] is! bool) {
      throw const FormatException('Invalid schedule preview');
    }
    PreviewReceipt? receipt;
    if (data['candidate'] == true) {
      if (data['reason'] != 'DUE_INSTANCE_DRY_RUN') {
        throw const FormatException('Invalid due reason');
      }
      final envelope = object(data['request']);
      final id = object(envelope['request'])['request_id'];
      if (id is! String || !RegExp(r'^schedule_[a-f0-9]{48}$').hasMatch(id)) {
        throw const FormatException('Invalid scheduled ID');
      }
      receipt = PreviewReceipt.decode(
        jsonEncode(envelope),
        id,
        '',
        source: 'SCHEDULED',
      );
    } else if (![
          'TIME_INVALID',
          'PLAN_DISABLED',
          'NOT_SCHEDULED_TODAY',
          'NOT_DUE',
          'MISSED_WINDOW_NO_CATCHUP',
          'ESP32_UNAVAILABLE_NO_QUEUE',
          'SAFETY_STATE_UNKNOWN_OR_UNSAFE_NO_QUEUE',
        ].contains(data['reason']) ||
        data['request'] != null) {
      throw const FormatException('Invalid noncandidate preview');
    }
    return SchedulePreview._(data, receipt);
  }
  String get reason => text(data['reason']);
  bool get candidate => data['candidate'] == true;
}
