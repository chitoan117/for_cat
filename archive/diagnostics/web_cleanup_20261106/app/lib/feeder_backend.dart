import 'package:flutter/foundation.dart';

import 'feeder_state.dart';
import 'meal_plans.dart';
import 'history_model.dart';
import 'status_model.dart';

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
  dog,
  ultrasonicTimeout,
  stale,
  hxCalibrated,
}

abstract class FeederBackend extends ChangeNotifier {
  FeederState state = FeederState.unknown();
  bool feeding = false; // request in flight, NEVER a claim of servo movement
  PreviewReceipt? receipt;
  String? requestError;
  String? connectionError;
  final List<String> activity = [];
  final List<HistoryEntry> historyRecords = [];
  bool historyLoaded = false, plansLoaded = false;
  String? historyError;
  AppStatus connectionStatus = AppStatus.unknown;
  Map<String, dynamic>? calibrationInfo;
  bool? calibrationSupported;
  String? calibrationError;
  String get endpoint => 'Chưa cấu hình';
  final List<MealPlan> mealPlans = [];
  bool plansBusy = false;
  String? plansError;
  SchedulePreview? schedulePreview;
  PreviewReceipt? scheduledReceipt;
  ScheduledWorkerStatus scheduledWorker = ScheduledWorkerStatus.unknown();
  final List<Map<String, dynamic>> scheduledOccurrences = [];
  final List<MealPreferenceResult> mealPreferenceLogs =
      List<MealPreferenceResult>.of(defaultMealPreferenceLogs);
  String selectedFood = 'FOOD_A';

  void selectFood(String food) {
    selectedFood = food.trim().toUpperCase().contains('B')
        ? 'FOOD_B'
        : 'FOOD_A';
    notifyListeners();
  }

  MealPreferenceResult recordMealPreference({
    String? food,
    double startingGrams = 35.0,
    required double remainingGrams,
    DateTime? timestamp,
    bool addToHistoryRecords = false,
  }) {
    final result = evaluateMealPreference(
      food: food ?? selectedFood,
      startingGrams: startingGrams,
      remainingGrams: remainingGrams,
      timestamp: timestamp,
    );
    mealPreferenceLogs.insert(0, result);
    if (addToHistoryRecords) {
      historyRecords.insert(0, HistoryEntry.fromMealPreference(result));
    }
    notifyListeners();
    return result;
  }

  bool get isMock;
  bool get online => state.online;
  bool get canFeed => !feeding && state.canPreview;
  Future<void> start();
  Future<void> feed();
  Future<void> refreshHistory();
  Future<void> refreshCalibration() async {}
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
