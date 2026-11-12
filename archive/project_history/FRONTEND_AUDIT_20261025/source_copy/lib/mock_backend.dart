import 'package:flutter/foundation.dart';

enum DemoScenario {
  normal,
  ownerCat,
  feeding,
  success,
  cooldown,
  dailyLimit,
  foodEmpty,
  waterLow,
  sensorFault,
  offline,
}

class MockFeederBackend extends ChangeNotifier {
  DemoScenario scenario = DemoScenario.normal;
  bool feeding = false;
  final List<String> activity = <String>[];

  bool get online => scenario != DemoScenario.offline;

  void setScenario(DemoScenario value) {
    scenario = value;
    feeding = value == DemoScenario.feeding;
    notifyListeners();
  }

  Future<void> feed() async {
    if (feeding || !online) return;
    feeding = true;
    notifyListeners();

    await Future<void>.delayed(const Duration(milliseconds: 900));
    feeding = false;
    scenario = DemoScenario.success;
    activity.insert(0, 'Đã cho ăn thành công · 40 g');
    notifyListeners();
  }
}
