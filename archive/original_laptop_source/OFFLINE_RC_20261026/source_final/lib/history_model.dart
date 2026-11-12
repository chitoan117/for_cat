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
    final kind = text(event['kind'], '');
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

  String get legacyText =>
      '${timestamp?.toIso8601String() ?? 'Chưa có timestamp'} · ${category == HistoryCategory.feeding ? 'DRY RUN' : source} · $source · $reason';
}

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
