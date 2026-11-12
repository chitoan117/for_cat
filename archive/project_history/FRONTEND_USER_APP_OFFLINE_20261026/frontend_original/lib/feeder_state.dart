import 'dart:convert';

Map<String, dynamic> object(Object? value) =>
    value is Map<String, dynamic> ? value : <String, dynamic>{};
double? number(Object? value) =>
    value is num && value.isFinite ? value.toDouble() : null;
String text(Object? value, [String fallback = 'UNKNOWN']) =>
    value is String ? value : fallback;

class FeederState {
  final Map<String, dynamic> data;
  const FeederState._(this.data);

  factory FeederState.unknown({
    String source = 'REAL',
    String health = 'ESP32_DISCONNECTED',
  }) => FeederState._({
    'data_source': source,
    'esp32': {'connected': false, 'health': health},
    'ai': {'classification': 'UNKNOWN', 'health': 'DISCONNECTED'},
    'weight': {'calibrated': false, 'grams': null, 'health': 'UNKNOWN'},
  });

  factory FeederState.decode(String body, {bool allowMock = false}) {
    if (body.length > 65536) throw const FormatException('State too large');
    final data = object(jsonDecode(body));
    if (data['schema_version'] != 'system_state_v1' ||
        (data['data_source'] != 'REAL' &&
            !(allowMock && data['data_source'] == 'MOCK'))) {
      throw const FormatException('Not the canonical SystemState');
    }
    final ai = object(data['ai']);
    if (!['CAT', 'DOG', 'NONE', 'UNKNOWN'].contains(ai['classification'])) {
      throw const FormatException('Invalid AI class');
    }
    for (final key in ['food', 'water']) {
      if (data['${key}_reservoir_sensor'] == 'NOT_WIRED' &&
          data['${key}_reservoir_percent'] != null) {
        throw const FormatException('Unwired inventory has a value');
      }
    }
    final safety = object(data['safety']);
    for (final key in [
      'servo_armed',
      'pump_armed',
      'auto_feed',
      'auto_water',
    ]) {
      if (safety[key] != null && safety[key] is! bool) {
        throw const FormatException('Invalid safety flag');
      }
    }
    return FeederState._(data);
  }

  String get source => text(data['data_source'], 'REAL');
  Map<String, dynamic> get esp32 => object(data['esp32']);
  bool get online =>
      esp32['connected'] == true && esp32['health'] == 'ESP32_CONNECTED';
  String get linkHealth => text(esp32['health']);
  Map<String, dynamic> sensor(String name) => object(data[name]);
  Map<String, dynamic> get ai => object(data['ai']);
  String get classification =>
      ai['health'] == 'ONLINE' ? text(ai['classification']) : 'UNKNOWN';
  double? get confidence {
    final value = number(ai['confidence']);
    return classification != 'UNKNOWN' &&
            value != null &&
            value >= 0 &&
            value <= 1
        ? value
        : null;
  }

  double? distance(String role) {
    final value = number(sensor(role)['distance_cm']);
    return online &&
            sensor(role)['valid'] == true &&
            value != null &&
            value > 0 &&
            value <= 400
        ? value
        : null;
  }

  String health(String role) =>
      online ? text(sensor(role)['health']) : linkHealth;
  double? get rawCounts {
    final value = number(sensor('weight')['raw_counts']);
    return online &&
            sensor('weight')['raw_available'] == true &&
            value != null &&
            value >= -8388608 &&
            value <= 8388607
        ? value
        : null;
  }

  String get calibrationState =>
      online ? text(sensor('weight')['calibration_state']) : linkHealth;
  String get stabilityState =>
      online ? text(sensor('weight')['stability_state']) : 'UNKNOWN';
  bool? get weightStable => online && sensor('weight')['stable'] is bool
      ? sensor('weight')['stable'] as bool
      : null;
  double? get tareCounts =>
      online ? number(sensor('weight')['tare_offset_counts']) : null;
  double? get gramsPerCount =>
      online ? number(sensor('weight')['grams_per_count']) : null;
  double? get weightAge =>
      online ? number(sensor('weight')['age_seconds']) : null;
  int? get weightSamples =>
      online && sensor('weight')['raw_window_samples'] is int
      ? sensor('weight')['raw_window_samples'] as int
      : null;
  bool get calibrated =>
      online &&
      sensor('weight')['calibrated'] == true &&
      sensor('weight')['calibration_valid'] == true &&
      sensor('weight')['calibration_authority'] ==
          'JETSON_SQLITE_PHYSICAL_REFERENCE_V1' &&
      [
        'CALIBRATED',
        'CALIBRATED_PENDING_PERSISTENCE',
      ].contains(sensor('weight')['calibration_state']);
  double? get grams => calibrated ? number(sensor('weight')['grams']) : null;
  double? inventory(String role) {
    if (!online || data['${role}_reservoir_sensor'] == 'NOT_WIRED') return null;
    final value = number(data['${role}_reservoir_percent']);
    return value != null && value >= 0 && value <= 100 ? value : null;
  }

  Map<String, dynamic> get safety => object(data['safety']);
  bool get canPreview =>
      online &&
      object(data['feed'])['target_grams'] == 35 &&
      object(data['feed'])['actuator_execution'] == false &&
      safety['actuator_execution'] == false &&
      safety['actuator_outputs_enabled'] == 0 &&
      [
        'servo_armed',
        'pump_armed',
        'auto_feed',
        'auto_water',
      ].every((key) => safety[key] == false);
  String get observedAt => text(data['observed_at'], '—');
}

class PreviewReceipt {
  final Map<String, dynamic> data;
  const PreviewReceipt._(this.data);
  factory PreviewReceipt.decode(
    String body,
    String id,
    String subSource, {
    String source = 'MANUAL',
  }) {
    if (!['MANUAL', 'SCHEDULED'].contains(source)) {
      throw ArgumentError('Invalid preview source');
    }
    if (body.length > 16384) throw const FormatException('Receipt too large');
    final data = object(jsonDecode(body));
    final request = object(data['request']);
    if (request['request_id'] != id ||
        request['source'] != source ||
        request['sub_source'] != subSource ||
        request['target_grams'] != 35 ||
        request['actuator_execution'] != false ||
        request['actual_dispensed_grams'] != null) {
      throw const FormatException('Receipt does not match dry-run request');
    }
    if (!data.containsKey('decision')) {
      throw const FormatException('Missing decision');
    }
    if (data['decision'] != null) {
      final decision = object(data['decision']);
      if (decision['request_id'] != id ||
          decision['source'] != source ||
          decision['sub_source'] != subSource ||
          decision['target_grams'] != 35 ||
          decision['status'] != 'DRY_RUN_BLOCKED' ||
          decision['reason'] != 'UNATTENDED_SAFE_MODE' ||
          decision['actuator_execution'] != false ||
          decision['actual_dispensed_grams'] != null) {
        throw const FormatException('Unsafe/invalid dry-run decision');
      }
    }
    return PreviewReceipt._(data);
  }
  Map<String, dynamic> get request => object(data['request']);
  Map<String, dynamic> get decision => object(data['decision']);
  bool get complete => data['decision'] != null;
  String get id => text(request['request_id']);
  String get reason => text(decision['qualification_reason'], 'QUEUED');
}
