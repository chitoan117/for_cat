import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:feeder_demo/ui_widgets.dart';

class FeedTransaction {
  final int id;
  final String source, state, measurementSource, servoCommand;
  final double? actual, observed;
  final bool finalReceived;
  const FeedTransaction(this.id, this.source, this.state, this.measurementSource,
      this.actual, this.observed, this.finalReceived, this.servoCommand);

  static double? number(Object? value) {
    if (value == null) return null;
    if (value is! num || !value.toDouble().isFinite) {
      throw const FormatException('Invalid mass');
    }
    return value.toDouble();
  }

  factory FeedTransaction.decode(Map<String, dynamic> value, String context) {
    final id = value['request_id'];
    if (id is! int || id < 1 || id > 0xffffff) {
      throw const FormatException('Invalid request identity');
    }
    final policy = value['mass_policy'];
    if (policy is! Map || policy['target_grams'] != 35 ||
        policy['tolerance_grams'] != 5 || policy['minimum_accepted_grams'] != 30 ||
        policy['maximum_accepted_grams'] != 40 || policy['inclusive_bounds'] != true) {
      throw const FormatException('Mass policy mismatch');
    }
    final source = value['source'];
    final state = value['state'];
    if (!['REAL', 'MOCK', 'NOT_AVAILABLE'].contains(source) ||
        !['SENT', 'PENDING', 'UNKNOWN_OUTCOME', 'REJECTED', 'FAULT', 'COMPLETE'].contains(state)) {
      throw const FormatException('Unknown source/state');
    }
    if (source == 'REAL' && (context == 'OFFLINE_SANDBOX' ||
        value['capture_verified'] != true || value['measurement_source'] != 'ESP32_HX711_CLOSED_LOOP')) {
      throw const FormatException('Unverified REAL claim');
    }
    final actual = number(value['actual_dispensed_grams']);
    final observed = number(value['latest_observed_grams']);
    final finalReceived = value['final_status_received'] == true;
    if (!finalReceived && actual != null) {
      throw const FormatException('ACK is not a final mass');
    }
    if (state == 'COMPLETE' && (source == 'NOT_AVAILABLE' || !finalReceived ||
        actual == null || actual < 30 || actual > 40 || value['mass_in_band'] != true ||
        value['closed'] != true || value['settled'] != true || value['pwm_off'] != true ||
        value['journal_committed'] != true || value['calibration_valid'] != true)) {
      throw const FormatException('Incomplete safety/final proof');
    }
    return FeedTransaction(id, source as String, state as String,
        value['measurement_source'] as String? ?? 'NOT_AVAILABLE', actual, observed, finalReceived,
        value['servo_command_state'] as String? ?? 'UNKNOWN');
  }

  String get label => switch (state) {
    'COMPLETE' => '$source · COMPLETE — final FEED_STATUS',
    'SENT' || 'PENDING' => '$source · PENDING — ACK chưa xác nhận cấp xong',
    'UNKNOWN_OUTCOME' => '$source · UNKNOWN — không tự gửi lại',
    _ => '$source · $state',
  };
  String get actualLabel => actual == null ? 'Chưa có dữ liệu' : '${actual!.toStringAsFixed(2)} g';
}

List<FeedTransaction> decodeHistory(Map<String, dynamic> data) {
  if (data['schema_version'] != 'forcat_closed_loop_view_v1' || data['items'] is! List ||
      (data['items'] as List).length > 100) {
    throw const FormatException('History schema/budget');
  }
  final context = data['execution_context'];
  if (!['OFFLINE_SANDBOX', 'QUALIFIED_DEVICE_RECEIPT'].contains(context)) {
    throw const FormatException('Missing provenance');
  }
  return (data['items'] as List).map((item) => FeedTransaction.decode(
      Map<String, dynamic>.from(item as Map), context as String)).toList();
}

class ClosedLoopHistoryController extends ChangeNotifier {
  final http.Client client;
  final Uri base;
  final Map<String, String> headers;
  List<FeedTransaction> entries = [];
  String sourceStatus = 'NOT_AVAILABLE';
  bool _disposed = false;
  int _generation = 0;
  ClosedLoopHistoryController(this.client, this.base, {this.headers = const {}});

  Future<void> refresh() async {
    final generation = ++_generation;
    try {
      final response = await client.get(base.resolve('/api/v1/closed-loop/history'),
          headers: headers).timeout(const Duration(seconds: 2));
      if (response.statusCode != 200 || response.bodyBytes.length > 262144) {
        throw const FormatException('History unavailable');
      }
      final next = decodeHistory(Map<String, dynamic>.from(jsonDecode(response.body) as Map));
      if (_disposed || generation != _generation) return;
      entries = next;
      sourceStatus = next.isEmpty ? 'NOT_AVAILABLE' : next.map((e) => e.source).toSet().join('/');
    } catch (_) {
      if (_disposed || generation != _generation) return;
      entries = [];
      sourceStatus = 'NOT_AVAILABLE';
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    super.dispose();
  }
}

class ClosedLoopHistoryPanel extends StatelessWidget {
  final List<FeedTransaction> entries;
  const ClosedLoopHistoryPanel({super.key, required this.entries});
  @override
  Widget build(BuildContext context) => AppCard(child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Text('Kết quả cấp thức ăn · target 35 g · final 30–40 g'),
      if (entries.isEmpty) const Text('NOT_AVAILABLE — chưa có kết quả'),
      for (final entry in entries) ...[
        Text('#${entry.id} ${entry.label}'),
        Text('Khối lượng thực: ${entry.actualLabel}'),
        Text('Quan sát cuối: ${entry.observed == null ? 'Chưa có dữ liệu' : '${entry.observed!.toStringAsFixed(2)} g'}'),
        Text('Measurement source: ${entry.measurementSource}'),
        Text('GPIO6 · lệnh: ${entry.servoCommand} · không phải phản hồi vị trí cửa'),
      ],
    ],
  ));
}
