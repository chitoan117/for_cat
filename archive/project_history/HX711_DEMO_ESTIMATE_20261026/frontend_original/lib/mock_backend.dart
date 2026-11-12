import 'dart:convert';
import 'feeder_backend.dart';
import 'feeder_state.dart';
export 'feeder_backend.dart' show DemoScenario;

/// Explicit development-only fixture. Never selected as a REAL fallback.
class MockFeederBackend extends FeederBackend {
  DemoScenario scenario = DemoScenario.normal;
  MockFeederBackend() { setScenario(scenario); }
  @override bool get isMock => true;
  void setScenario(DemoScenario value) {
    scenario = value;
    final online = value != DemoScenario.offline;
    state = FeederState.decode(jsonEncode({
      'schema_version': 'system_state_v1', 'data_source': 'MOCK',
      'esp32': {'connected': online, 'health': online ? 'ESP32_CONNECTED' : 'ESP32_DISCONNECTED'},
      'ai': {'classification': value == DemoScenario.ownerCat ? 'CAT' : 'NONE', 'health': online ? 'ONLINE' : 'DISCONNECTED', 'confidence': value == DemoScenario.ownerCat ? .94 : null},
      'food_reservoir_sensor': 'MOCK', 'food_reservoir_percent': value == DemoScenario.foodEmpty ? 0 : 75,
      'water_reservoir_sensor': 'MOCK', 'water_reservoir_percent': value == DemoScenario.waterLow ? 12 : 82,
      'weight': {'calibrated': false, 'grams': null, 'health': 'NOT_CALIBRATED'},
      'feed': {'target_grams': 35, 'actuator_execution': false},
      'safety': {'servo_armed': false, 'pump_armed': false, 'auto_feed': false, 'auto_water': false, 'actuator_outputs_enabled': 0, 'actuator_execution': false}
    }), allowMock: true);
    notifyListeners();
  }
  @override Future<void> start() async {}
  @override Future<void> refreshHistory() async {}
  @override Future<void> feed() async {
    if (!canFeed) return;
    feeding = true; notifyListeners();
    await Future<void>.delayed(const Duration(milliseconds: 100));
    feeding = false; scenario = DemoScenario.success;
    activity.insert(0, 'MOCK · request DRY RUN 35 g · không cấp thức ăn');
    notifyListeners();
  }
}
