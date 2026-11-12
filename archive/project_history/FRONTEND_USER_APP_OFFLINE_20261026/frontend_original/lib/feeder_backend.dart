import 'package:flutter/foundation.dart';

import 'feeder_state.dart';
import 'meal_plans.dart';

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

abstract class FeederBackend extends ChangeNotifier {
  FeederState state = FeederState.unknown();
  bool feeding = false; // request in flight, NEVER a claim of servo movement
  PreviewReceipt? receipt;
  String? requestError;
  String? connectionError;
  final List<String> activity = [];
  final List<MealPlan> mealPlans = [];
  bool plansBusy = false;
  String? plansError;
  SchedulePreview? schedulePreview;
  PreviewReceipt? scheduledReceipt;
  ScheduledWorkerStatus scheduledWorker = ScheduledWorkerStatus.unknown();
  final List<Map<String, dynamic>> scheduledOccurrences = [];
  bool get isMock;
  bool get online => state.online;
  bool get canFeed => !feeding && state.canPreview;
  Future<void> start();
  Future<void> feed();
  Future<void> refreshHistory();
  Future<void> refreshMealPlans() async {}
  Future<void> saveMealPlan({
    MealPlan? existing,
    required String name,
    required String localTime,
    required List<int> weekdays,
    required bool enabled,
  }) async => throw UnsupportedError('REAL only');
  Future<void> deleteMealPlan(MealPlan plan) async =>
      throw UnsupportedError('REAL only');
  Future<void> previewMealPlan(MealPlan plan) async =>
      throw UnsupportedError('REAL only');
}
