import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'ui_widgets.dart';

class ReservoirCard extends StatelessWidget {
  final FeederState state;
  final String role;
  const ReservoirCard({super.key, required this.state, required this.role});
  @override
  Widget build(BuildContext context) {
    final water = role == 'water';
    final view = object(object(state.data['reservoirs'])[role]);
    final fresh = state.online && view['valid'] == true;
    final raw = fresh ? number(view['percent']) : null;
    final value = raw != null && raw >= 0 && raw <= 100 ? raw : null;
    final color = water ? appBlue : appOrange;
    final label = !fresh
        ? 'Chưa có dữ liệu'
        : view['state'] == 'EMPTY'
        ? 'Đã cạn'
        : value == null
        ? 'Cần lưu mức đầy'
        : value >= 99
        ? 'Đầy'
        : value <= 20
        ? 'Sắp hết'
        : 'Còn sử dụng';
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                water ? Icons.water_drop_outlined : Icons.rice_bowl_outlined,
                color: color,
                size: 20,
              ),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  water ? 'Nước dự trữ' : 'Thức ăn dự trữ',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            value == null ? '—' : '${value.toStringAsFixed(0)}%',
            style: TextStyle(
              color: color,
              fontSize: 29,
              height: 1.1,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 9),
          if (value != null) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: value / 100,
                color: color,
                backgroundColor: color.withValues(alpha: .1),
                minHeight: 5,
              ),
            ),
            const SizedBox(height: 7),
          ],
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: Color(0xff827871)),
          ),
        ],
      ),
    );
  }
}

class ReservoirCalibrationPanel extends StatelessWidget {
  final FeederBackend backend;
  const ReservoirCalibrationPanel({super.key, required this.backend});
  Future<void> save(BuildContext context, String role) async {
    final title = role == 'water' ? 'bình nước' : 'hộp thức ăn';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Lưu mức đầy $title?'),
        content: Text(
          'Chỉ xác nhận khi $title đã được bổ sung đến mức đầy sử dụng. Giữ nguyên cảm biến trong lúc lấy số đo. Mốc này sẽ tương ứng 100%.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    final ok = await backend.saveReservoirFull(role, confirmed: true);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? 'Đã lưu mức đầy 100%.'
              : backend.reservoirError ?? 'Chưa lưu được mức đầy.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: backend,
    builder: (context, _) {
      final levels = object(backend.state.data['reservoirs']);
      return AppCard(
        child: ExpansionTile(
          tilePadding: EdgeInsets.zero,
          childrenPadding: EdgeInsets.zero,
          title: const Text(
            'Mức dự trữ',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
          children: [
            const Text(
              'Mốc cạn đã lưu. Khi bổ sung đầy, lưu mức đầy để tính phần trăm.',
              style: TextStyle(fontSize: 12),
            ),
            for (final role in ['food', 'water'])
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${role == 'food' ? 'Thức ăn' : 'Nước'} · ${object(levels[role])['calibration'] == 'READY' ? 'Đã hiệu chuẩn' : 'Chưa lưu mức đầy'}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                    TextButton(
                      onPressed:
                          backend.online &&
                              !backend.isMock &&
                              !backend.reservoirBusy
                          ? () => save(context, role)
                          : null,
                      child: Text(
                        role == 'food' ? 'Lưu đầy thức ăn' : 'Lưu đầy nước',
                      ),
                    ),
                  ],
                ),
              ),
            if (backend.reservoirBusy)
              const Padding(
                padding: EdgeInsets.all(8),
                child: Text('Đang lấy số đo…'),
              ),
          ],
        ),
      );
    },
  );
}
