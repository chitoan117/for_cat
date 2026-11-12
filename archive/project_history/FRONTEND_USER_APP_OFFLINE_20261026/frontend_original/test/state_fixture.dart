import 'dart:convert';

Map<String, dynamic> fixture({bool connected = true, String classification = 'CAT', double distance = 24.8}) => {
  'schema_version': 'system_state_v1', 'data_source': 'REAL', 'observed_at': 'SYNTHETIC_TEST_ONLY',
  'esp32': {'connected': connected, 'health': connected ? 'ESP32_CONNECTED' : 'ESP32_DISCONNECTED'},
  'ai': {'classification': classification, 'health': 'ONLINE', 'confidence': classification == 'CAT' ? .91 : null},
  'approach': {'distance_cm': distance, 'valid': true, 'health': 'NOT_CALIBRATED'},
  'water_operational': {'distance_cm': 25.9, 'valid': true, 'health': 'NOT_CALIBRATED'},
  'weight': {'raw_counts': -675000, 'raw_available': true, 'calibrated': false, 'grams': null, 'health': 'NOT_CALIBRATED'},
  'food_reservoir_sensor': 'NOT_WIRED', 'food_reservoir_percent': null,
  'water_reservoir_sensor': 'NOT_WIRED', 'water_reservoir_percent': null,
  'time': {'time_valid': false}, 'feed': {'target_grams': 35, 'actuator_execution': false},
  'safety': {'servo_armed': false, 'pump_armed': false, 'auto_feed': false, 'auto_water': false,
    'actuator_outputs_enabled': 0, 'actuator_execution': false}
};

String preview(Map<String, dynamic> payload, {bool complete = true, bool unsafe = false}) => jsonEncode({
  'request': {...payload, 'source': 'MANUAL', 'timestamp': 'SYNTHETIC_TEST_ONLY', 'actuator_execution': false, 'actual_dispensed_grams': null},
  'decision': complete ? {'request_id': payload['request_id'], 'source': 'MANUAL', 'sub_source': payload['sub_source'],
    'target_grams': 35, 'status': 'DRY_RUN_BLOCKED', 'reason': 'UNATTENDED_SAFE_MODE',
    'qualification_reason': 'WEIGHT_NOT_CALIBRATED', 'actuator_execution': unsafe, 'actual_dispensed_grams': null} : null
});
