class DiagnosticsPage extends StatelessWidget {
  final FeederBackend backend;
  const DiagnosticsPage({super.key, required this.backend});

  @override
  Widget build(BuildContext context) {
    final s = backend.state;
    return ListView(
      key: const PageStorageKey('system'),
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
      children: [
        const PageHeading('Hệ thống'),
        DiagnosticSection(title: 'Kết nối', icon: Icons.wifi_outlined, children: [
          _ConnectionRow('Máy chủ', backend.connectionStatus),
          _ConnectionRow('Bộ điều khiển', parseStatus(s.linkHealth)),
          _ConnectionRow('Nhận diện', parseStatus(s.ai['health'])),
        ]),
        DiagnosticSection(title: 'Nhận diện', icon: Icons.pets_outlined, children: [
          Text(s.classification == 'CAT' ? 'Đã phát hiện mèo' : s.classification == 'DOG' ? 'Phát hiện chó' : s.classification == 'NONE' ? 'Chờ mèo tới' : 'Chưa có dữ liệu', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          if (s.confidence != null) InfoNote('Độ tin cậy ${(s.confidence! * 100).toStringAsFixed(0)}%'),
        ]),
        DiagnosticSection(title: 'Cân thức ăn', icon: Icons.scale_outlined, children: [
          Text(s.grams == null ? 'Chưa có dữ liệu' : '${s.grams!.toStringAsFixed(1)} g', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          StatusPill(parseStatus(s.calibrationState)),
        ]),
        DiagnosticSection(title: 'Cảm biến khoảng cách', icon: Icons.sensors_outlined, children: [
          for (final sensor in UltrasonicState.fromSystem(s)) Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_sensorLabel(sensor.sensorId), style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                StatusPill(sensor.state),
              ])),
              const SizedBox(width: 8),
              Text(sensor.distanceCm == null ? '—' : '${sensor.distanceCm!.toStringAsFixed(1)} cm', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            ]),
          ),
        ]),
        DiagnosticSection(title: 'Thiết bị', icon: Icons.memory_outlined, children: [
          _ConnectionRow('Màn hình', parseStatus(s.health('oled'))),
          _ConnectionRow('Nút cho ăn', parseStatus(s.health('manual_button')), label: s.online && s.sensor('manual_button')['pressed'] is bool ? s.sensor('manual_button')['pressed'] == true ? 'Đang nhấn' : 'Đã thả' : null),
          _ConnectionRow('Lịch tự động', parseStatus(backend.scheduledWorker.status), label: workerStatusText(backend.scheduledWorker.status)),
        ]),
        AppCard(child: ExpansionTile(tilePadding: EdgeInsets.zero, title: const Text('Chẩn đoán kỹ thuật', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)), children: [TechnicalDiagnostics(backend: backend)])),
      ],
    );
  }
}

String _sensorLabel(String id) => switch (id.toUpperCase()) {
  'HC_SR04_1' => 'Mèo tới',
  'HC_SR04_2' => 'Hộp thức ăn',
  'JSN_SR04T_1' => 'Chén nước',
  'JSN_SR04T_2' => 'Bình nước',
  _ => id,
};

class _ConnectionRow extends StatelessWidget {
  final String name;
  final AppStatus status;
  final String? label;
  const _ConnectionRow(this.name, this.status, {this.label});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 7),
    child: Row(children: [Expanded(child: Text(name, style: const TextStyle(fontWeight: FontWeight.w500))), const SizedBox(width: 10), StatusPill(status, label: label)]),
  );
}
