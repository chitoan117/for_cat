import 'package:flutter/foundation.dart';
import 'feeder_state.dart';

enum DemoScenario { normal, ownerCat, feeding, success, cooldown, dailyLimit, foodEmpty, waterLow, sensorFault, offline }

abstract class FeederBackend extends ChangeNotifier {
  FeederState state = FeederState.unknown();
  bool feeding = false; // request in flight, NEVER a claim of servo movement
  PreviewReceipt? receipt;
  String? requestError;
  String? connectionError;
  final List<String> activity = [];
  bool get isMock;
  bool get online => state.online;
  bool get canFeed => !feeding && state.canPreview;
  Future<void> start();
  Future<void> feed();
  Future<void> refreshHistory();
}
