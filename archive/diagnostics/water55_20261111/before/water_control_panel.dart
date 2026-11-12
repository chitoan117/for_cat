import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'ui_widgets.dart';

class WaterControlPanel extends StatelessWidget {
  final FeederBackend backend;
  const WaterControlPanel({super.key, required this.backend});
  Future<void> enable(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Bật chức năng nước?'),
        content: const Text(
          'Bơm có thể chạy khi cảm biến báo thiếu nước. Chỉ bật khi đã kiểm tra đường ống và có thể theo dõi.\n\nNếu nước vẫn tự chảy khi motor tắt, hãy xử lý đường ống trước.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Xác nhận bật'),
          ),
        ],
      ),
    );
    if (ok == true) await backend.setWaterEnabled(true, confirmed: true);
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: backend,
    builder: (context, _) {
      final s = backend.waterControl;
      final fresh = s?['fresh'] == true && s?['supported'] == true;
      final enabled = fresh && s?['enabled'] == true;
      final request = s?['request'];
      final requestState = request is Map ? request['status'] : null;
      final pending = requestState == 'PENDING' || requestState == 'DISPATCHED';
      final fault = fresh && s?['fault'] == true;
      final canEnable =
          fresh &&
          s?['can_enable'] == true &&
          !enabled &&
          !pending &&
          !backend.waterBusy &&
          !backend.isMock;
      final label = !fresh
          ? 'Chưa có kết nối thiết bị'
          : fault
          ? 'Đã dừng do lỗi'
          : enabled
          ? (s?['running'] == true ? 'Đang bơm' : 'Đang theo dõi mức nước')
          : 'Đang tắt';
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.water_drop_outlined, color: appBlue),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Chức năng nước',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                ),
                Text(
                  !fresh
                      ? 'Chưa rõ'
                      : enabled
                      ? 'Đang bật'
                      : 'Đang tắt',
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xff655b57),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (label != 'Đang tắt')
              Text(
                label,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            Text(
              enabled
                  ? 'Tự kiểm tra và cấp nước theo cảm biến D1.'
                  : 'Tạm dừng tự cấp nước. Chỉ bật sau khi bạn xác nhận.',
              style: const TextStyle(fontSize: 13),
            ),
            if (enabled)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Chén: ${cmText((s?['d1_cm'] as num?)?.toDouble())}    Bình: ${cmText((s?['d2_cm'] as num?)?.toDouble())}',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (!enabled)
                  FilledButton.icon(
                    onPressed: canEnable ? () => enable(context) : null,
                    icon: const Icon(Icons.water_drop_outlined),
                    label: const Text('Bật chức năng nước'),
                  ),
                OutlinedButton.icon(
                  onPressed: !backend.waterBusy && !backend.isMock
                      ? () => backend.setWaterEnabled(false)
                      : null,
                  icon: const Icon(Icons.stop_circle_outlined),
                  label: const Text('Tắt bơm'),
                ),
              ],
            ),
            if (pending || backend.waterBusy)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Đang chờ ESP32 xác nhận…',
                  style: TextStyle(fontSize: 12),
                ),
              ),
            if (request is Map &&
                [
                  'REJECTED',
                  'TIMEOUT',
                  'EXPIRED',
                  'CANCELLED',
                ].contains(requestState))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  request['note']?.toString() ?? 'Chưa áp dụng thao tác.',
                  style: const TextStyle(fontSize: 12, color: Colors.brown),
                ),
              ),
            if (backend.waterError != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  backend.waterError!,
                  style: const TextStyle(fontSize: 12, color: Colors.brown),
                ),
              ),
          ],
        ),
      );
    },
  );
}

class WaterReservoirCard extends StatelessWidget {
  final FeederBackend backend;
  const WaterReservoirCard({super.key, required this.backend});
  @override
  Widget build(BuildContext context) {
    final s = backend.waterControl;
    final on = s?['fresh'] == true && s?['enabled'] == true;
    final cm = on ? (s?['d2_cm'] as num?)?.toDouble() : null;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.water_drop_outlined, color: appBlue),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Nước dự trữ',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            cm == null ? '—' : '${cm.toStringAsFixed(1)} cm',
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: appBlue,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            on
                ? (cm == null
                      ? 'Chưa có số đo D2'
                      : 'Khoảng cách từ D2 đến mặt nước')
                : 'Tạm dừng theo dõi nước',
            style: const TextStyle(fontSize: 12, color: Color(0xff827871)),
          ),
        ],
      ),
    );
  }
}
