import 'feeder_state.dart';
import 'status_model.dart';

enum HistoryCategory { all, feeding, water, ai, system }

extension HistoryCategoryText on HistoryCategory {
  String get label => switch (this) {
    HistoryCategory.all => 'Tất cả',
    HistoryCategory.feeding => 'Cho ăn',
    HistoryCategory.water => 'Nước',
    HistoryCategory.ai => 'AI',
    HistoryCategory.system => 'Hệ thống',
  };
}

class HistoryEntry {
  final String id, title, source, reason, provenance;
  final HistoryCategory category;
  final DateTime? timestamp;
  final AppStatus status;
  final double? targetGrams;
  final Map<String, dynamic> details;
  const HistoryEntry({
    required this.id,
    required this.title,
    required this.category,
    required this.timestamp,
    required this.source,
    required this.status,
    required this.reason,
    required this.provenance,
    required this.details,
    this.targetGrams,
  });

  static DateTime? stamp(Object? value) =>
      value is String ? DateTime.tryParse(value) : null;
  static String titleFor(String source) => switch (source) {
    'SCHEDULED' => 'Lịch ăn tự động',
    'MANUAL' => 'Yêu cầu cho ăn thủ công',
    'AUTO_CAT' => 'Yêu cầu từ phát hiện mèo',
    _ => 'Yêu cầu cho ăn',
  };
  static HistoryEntry? dryRun(
    Map<String, dynamic> data, {
    required String origin,
    Object? timestamp,
    String? requestId,
    String? source,
    Map<String, dynamic>? raw,
  }) {
    final id = requestId ?? text(data['request_id'], '');
    final src = source ?? text(data['source']);
    if (id.isEmpty ||
        !['MANUAL', 'SCHEDULED', 'AUTO_CAT'].contains(src) ||
        data['actuator_execution'] != false ||
        ![null, 'QUEUED', 'DRY_RUN_BLOCKED'].contains(data['status']) ||
        data['actual_dispensed_grams'] != null ||
        data['target_grams'] != 35) {
      return null;
    }
    final status = data['status'] == 'DRY_RUN_BLOCKED'
        ? AppStatus.blocked
        : AppStatus.dryRun;
    return HistoryEntry(
      id: 'request:$id',
      title: titleFor(src),
      category: HistoryCategory.feeding,
      timestamp: stamp(timestamp ?? data['timestamp']),
      source: src,
      status: status,
      reason: text(
        data['qualification_reason'],
        text(data['reason'], 'QUEUED'),
      ),
      provenance: origin,
      targetGrams: 35,
      details: raw ?? data,
    );
  }

  static HistoryEntry? fromOccurrence(Map<String, dynamic> row) {
    final decision = object(row['decision']);
    return dryRun(
      {...row, ...decision, 'source': 'SCHEDULED'},
      origin: 'scheduled_occurrences',
      timestamp: row['created_at'],
      requestId: text(row['request_id'], ''),
      source: 'SCHEDULED',
      raw: row,
    );
  }

  static HistoryEntry? fromReceipt(PreviewReceipt receipt) => dryRun(
    {...receipt.request, ...receipt.decision},
    origin: 'canonical_request_receipt',
    raw: receipt.data,
  );

  static HistoryEntry? fromEvent(Object? raw) {
    final event = object(raw), data = object(object(raw)['details']);
    final kind = text(event['kind'], text(event['type'], ''));
    if (kind == 'meal_preference') {
      final sourceMap = data.isNotEmpty ? data : event;
      final food = text(
        sourceMap['food'],
        text(sourceMap['meal_food'], 'FOOD_A'),
      );
      final starting =
          number(sourceMap['starting_g']) ??
          number(sourceMap['meal_starting_g']);
      final remaining =
          number(sourceMap['remaining_g']) ??
          number(sourceMap['meal_remaining_g']);
      if (starting == null ||
          remaining == null ||
          starting <= 0 ||
          remaining < 0 ||
          remaining > starting) {
        return null;
      }
      final pref = evaluateMealPreference(
        food: food,
        startingGrams: starting,
        remainingGrams: remaining,
        timestamp: stamp(event['timestamp']) ?? DateTime.now().toUtc(),
      );
      return fromMealPreference(pref, raw: event);
    }
    if (kind == 'feed_request_dry_run') {
      return dryRun(
        data,
        origin: 'esp32_events',
        timestamp: event['timestamp'],
      );
    }
    if (kind == 'telemetry_sample' || kind.isEmpty) return null;
    if (['ai_transition', 'ai_classification_transition'].contains(kind)) {
      final value = text(data['classification']);
      if (!['CAT', 'DOG', 'NONE'].contains(value)) return null;
      return HistoryEntry(
        id: 'event:${event['seq'] ?? '${event['timestamp']}:$kind'}',
        title: switch (value) {
          'CAT' => 'Đã phát hiện mèo',
          'DOG' => 'Phát hiện chó',
          _ => 'Chưa phát hiện mèo',
        },
        category: HistoryCategory.ai,
        timestamp: stamp(event['timestamp']),
        source: 'AI',
        status: AppStatus.online,
        reason: value,
        provenance: 'esp32_events',
        details: event,
      );
    }
    if (!(kind.startsWith('serial_') ||
        kind.startsWith('bridge_') ||
        kind.startsWith('system_') ||
        kind == 'sensor_state')) {
      return null;
    }
    final code = text(data['health'], text(data['reason']));
    return HistoryEntry(
      id: 'event:${event['seq'] ?? '${event['timestamp']}:$kind'}',
      title: switch (kind) {
        'serial_connected' => 'ESP32 đã kết nối',
        'serial_disconnected' => 'ESP32 mất kết nối',
        'sensor_state' => 'Cập nhật trạng thái cảm biến',
        _ => 'Sự kiện hệ thống',
      },
      category: HistoryCategory.system,
      timestamp: stamp(event['timestamp']),
      source: 'SYSTEM',
      status: parseStatus(code),
      reason: code,
      provenance: 'esp32_events',
      details: event,
    );
  }

  static HistoryEntry fromMealPreference(
    MealPreferenceResult pref, {
    String source = 'PREFERENCE_ALGO',
    Map<String, dynamic>? raw,
  }) => HistoryEntry(
    id: 'pref:${pref.id}',
    title: pref.conclusion,
    category: HistoryCategory.feeding,
    timestamp: pref.timestamp,
    source: source,
    status: switch (pref.preference) {
      'LIKE' => AppStatus.healthy,
      'DISLIKE' => AppStatus.degraded,
      _ => AppStatus.dryRun,
    },
    reason: pref.preference,
    provenance: 'meal_preference_log',
    targetGrams: pref.startingGrams,
    details: raw ?? pref.toJson(),
  );

  String get legacyText =>
      '${timestamp?.toIso8601String() ?? 'Chưa có timestamp'} · ${category == HistoryCategory.feeding ? 'DRY RUN' : source} · $source · $reason';
}

class MealPreferenceResult {
  final String id;
  final String food;
  final String foodLabel;
  final double startingGrams;
  final double remainingGrams;
  final double consumedGrams;
  final double consumedRatioPct;
  final String preference; // 'LIKE', 'DISLIKE', 'MODERATE'
  final String conclusion;
  final String ruleExplanation;
  final DateTime timestamp;

  const MealPreferenceResult({
    required this.id,
    required this.food,
    required this.foodLabel,
    required this.startingGrams,
    required this.remainingGrams,
    required this.consumedGrams,
    required this.consumedRatioPct,
    required this.preference,
    required this.conclusion,
    required this.ruleExplanation,
    required this.timestamp,
  });

  bool get isLike => preference == 'LIKE';
  bool get isDislike => preference == 'DISLIKE';

  Map<String, dynamic> toJson() => {
    'type': 'meal_preference',
    'id': id,
    'food': food,
    'food_label': foodLabel,
    'starting_g': startingGrams,
    'remaining_g': remainingGrams,
    'consumed_g': consumedGrams,
    'consumed_ratio_pct': double.parse(consumedRatioPct.toStringAsFixed(1)),
    'preference': preference,
    'conclusion': conclusion,
    'rule_explanation': ruleExplanation,
    'timestamp': timestamp.toIso8601String(),
  };
}

MealPreferenceResult evaluateMealPreference({
  required String food,
  double startingGrams = 35.0,
  required double remainingGrams,
  DateTime? timestamp,
  String? id,
}) {
  final normalizedFood = food.trim().toUpperCase().contains('B')
      ? 'FOOD_B'
      : 'FOOD_A';
  final foodLabel = normalizedFood == 'FOOD_B' ? 'Món B' : 'Món A';
  final safeStarting = startingGrams <= 0 ? 35.0 : startingGrams;
  final safeRemaining = remainingGrams < 0
      ? 0.0
      : (remainingGrams > safeStarting ? safeStarting : remainingGrams);
  final consumed = safeStarting - safeRemaining;
  final ratioPct = (consumed / safeStarting) * 100.0;
  final ts = timestamp ?? DateTime.now().toUtc();

  // Thuật toán chuẩn:
  // - Ăn hơn phân nửa (> 50% lượng cấp, tức >= 18.0 g trên 35 g, ví dụ còn 2 g -> ăn 33 g) => LIKE (Mèo thích ăn)
  // - Không ăn hoặc chỉ ăn rất ít (<= 5.0 g trên 35 g, ví dụ ăn 0 g, 3 g, 5 g -> còn 30-35 g) => DISLIKE (Mèo không thích ăn)
  final String preference;
  final String conclusion;
  final String ruleExplanation;
  if (consumed > (safeStarting * 0.5)) {
    preference = 'LIKE';
    conclusion = 'Mèo thích ăn $foodLabel (LIKE)';
    ruleExplanation =
        'Cấp ${safeStarting.toStringAsFixed(0)} g $foodLabel, mèo ăn ${consumed.toStringAsFixed(1)} g (${ratioPct.toStringAsFixed(1)}% > 50%), chỉ còn ${safeRemaining.toStringAsFixed(1)} g => Kết luận: $conclusion.';
  } else if (consumed <= 5.5) {
    preference = 'DISLIKE';
    conclusion = 'Mèo không thích ăn $foodLabel (DISLIKE)';
    ruleExplanation =
        'Cấp ${safeStarting.toStringAsFixed(0)} g $foodLabel, mèo chỉ ăn ${consumed.toStringAsFixed(1)} g (<= 5 g), còn thừa ${safeRemaining.toStringAsFixed(1)} g => Kết luận: $conclusion.';
  } else {
    preference = 'MODERATE';
    conclusion = 'Mèo ăn mức trung bình $foodLabel (MODERATE)';
    ruleExplanation =
        'Cấp ${safeStarting.toStringAsFixed(0)} g $foodLabel, mèo ăn ${consumed.toStringAsFixed(1)} g (${ratioPct.toStringAsFixed(1)}%), còn ${safeRemaining.toStringAsFixed(1)} g => Kết luận: $conclusion.';
  }

  return MealPreferenceResult(
    id: id ?? '${normalizedFood}_${ts.millisecondsSinceEpoch}',
    food: normalizedFood,
    foodLabel: foodLabel,
    startingGrams: safeStarting,
    remainingGrams: safeRemaining,
    consumedGrams: consumed,
    consumedRatioPct: ratioPct,
    preference: preference,
    conclusion: conclusion,
    ruleExplanation: ruleExplanation,
    timestamp: ts,
  );
}

final List<MealPreferenceResult> defaultMealPreferenceLogs = [
  evaluateMealPreference(
    id: 'log_food_a_like_33g',
    food: 'FOOD_A',
    startingGrams: 35.0,
    remainingGrams: 2.0,
    timestamp: DateTime.parse('2026-10-30T08:15:00Z'),
  ),
  evaluateMealPreference(
    id: 'log_food_b_dislike_3g',
    food: 'FOOD_B',
    startingGrams: 35.0,
    remainingGrams: 32.0,
    timestamp: DateTime.parse('2026-10-30T12:30:00Z'),
  ),
  evaluateMealPreference(
    id: 'log_food_b_dislike_5g',
    food: 'FOOD_B',
    startingGrams: 35.0,
    remainingGrams: 30.0,
    timestamp: DateTime.parse('2026-10-30T17:45:00Z'),
  ),
  evaluateMealPreference(
    id: 'log_food_a_like_22g',
    food: 'FOOD_A',
    startingGrams: 35.0,
    remainingGrams: 13.0,
    timestamp: DateTime.parse('2026-10-29T19:00:00Z'),
  ),
];

List<HistoryEntry> mergeHistory(
  Iterable<HistoryEntry> events,
  Iterable<HistoryEntry> occurrences,
  Iterable<HistoryEntry> receipts,
) {
  final byId = <String, HistoryEntry>{};
  for (final item in [...events, ...receipts, ...occurrences]) {
    final old = byId[item.id];
    if (old != null &&
        old.status == AppStatus.blocked &&
        item.status == AppStatus.dryRun) {
      continue;
    }
    byId[item.id] = item;
  }
  final result = byId.values.toList()
    ..sort((a, b) {
      final time = (b.timestamp?.millisecondsSinceEpoch ?? -1).compareTo(
        a.timestamp?.millisecondsSinceEpoch ?? -1,
      );
      return time != 0 ? time : a.id.compareTo(b.id);
    });
  return result.take(100).toList();
}
