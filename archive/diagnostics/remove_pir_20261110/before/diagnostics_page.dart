import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'diagnostic_models.dart';
import 'status_model.dart';
import 'ui_widgets.dart';

class DiagnosticsPage extends StatelessWidget {
  final FeederBackend backend;
  const DiagnosticsPage({super.key, required this.backend});

  @override
  Widget build(BuildContext context) {
    final s = backend.state;
    return ListView(
      key: const ValueKey('system'),
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
      children: [
        const PageHeading('Hệ thống'),
        DiagnosticSection(
          title: 'Kết nối',
          icon: Icons.wifi_outlined,
          children: [
            _ConnectionRow('Máy chủ', backend.connectionStatus),
            _ConnectionRow('Bộ điều khiển', parseStatus(s.linkHealth)),
            _ConnectionRow('Nhận diện', parseStatus(s.ai['health'])),
          ],
        ),
        DiagnosticSection(
          title: 'Nhận diện',
          icon: Icons.pets_outlined,
          children: [
            Text(
              s.classification == 'CAT'
                  ? 'Đã phát hiện mèo'
                  : s.classification == 'DOG'
                  ? 'Phát hiện chó'
                  : s.classification == 'NONE'
                  ? 'Chờ mèo tới'
                  : 'Chưa có dữ liệu',
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
            if (s.confidence != null)
              InfoNote(
                'Độ tin cậy ${(s.confidence! * 100).toStringAsFixed(0)}%',
              ),
          ],
        ),
        DiagnosticSection(
          title: 'Cân thức ăn',
          icon: Icons.scale_outlined,
          children: [
            Text(
              s.grams == null
                  ? 'Chưa có dữ liệu'
                  : '${s.grams!.toStringAsFixed(1)} g',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            StatusPill(parseStatus(s.calibrationState)),
          ],
        ),
        DiagnosticSection(
          title: 'Cảm biến khoảng cách',
          icon: Icons.sensors_outlined,
          children: [
            for (final sensor in UltrasonicState.fromSystem(s))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _sensorLabel(sensor.sensorId),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 4),
                          StatusPill(sensor.state),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      sensor.distanceCm == null
                          ? '—'
                          : '${sensor.distanceCm!.toStringAsFixed(1)} cm',
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
        DiagnosticSection(
          title: 'Thiết bị',
          icon: Icons.memory_outlined,
          children: [
            _ConnectionRow('Màn hình', parseStatus(s.health('oled'))),
            _ConnectionRow(
              'Nút cho ăn',
              parseStatus(s.health('manual_button')),
              label: s.online && s.sensor('manual_button')['pressed'] is bool
                  ? s.sensor('manual_button')['pressed'] == true
                        ? 'Đang nhấn'
                        : 'Đã thả'
                  : null,
            ),
            _ConnectionRow(
              'Lịch tự động',
              parseStatus(backend.scheduledWorker.status),
              label: workerStatusText(backend.scheduledWorker.status),
            ),
          ],
        ),
        AppCard(
          child: ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: const Text(
              'Chẩn đoán kỹ thuật',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            ),
            children: [TechnicalDiagnostics(backend: backend)],
          ),
        ),
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
    child: Row(
      children: [
        Expanded(
          child: Text(
            name,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
        ),
        const SizedBox(width: 10),
        StatusPill(status, label: label),
      ],
    ),
  );
}

class TechnicalDiagnostics extends StatelessWidget {
  final FeederBackend backend;
  const TechnicalDiagnostics({super.key, required this.backend});
  @override
  Widget build(BuildContext context) {
    final s = backend.state, w = s.sensor('weight');
    return ListView(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      children: [
        const PageHeading(
          'Hệ thống',
          subtitle: 'Trạng thái thật và diagnostics',
        ),
        DiagnosticSection(
          title: 'Kết nối',
          icon: Icons.wifi,
          children: [
            _Device('Jetson / backend', backend.connectionStatus),
            _Device('ESP32-S3 USB', parseStatus(s.linkHealth)),
            _Device('AI TensorRT', parseStatus(s.ai['health'])),
            DetailValue('Nguồn dữ liệu', s.source),
            DetailValue(
              'Giờ Jetson',
              object(s.data['time'])['time_valid'] == true
                  ? 'TIME_VALID'
                  : object(s.data['time'])['time_valid'] == false
                  ? 'TIME_INVALID'
                  : 'UNKNOWN',
            ),
          ],
        ),
        DiagnosticSection(
          title: 'AI',
          icon: Icons.pets,
          children: [
            StatusPill(parseStatus(s.ai['health']), showCode: true),
            DetailValue('Phân loại hiện tại', s.classification),
            DetailValue(
              'Độ tin cậy',
              s.confidence == null
                  ? 'Chưa có dữ liệu'
                  : '${(s.confidence! * 100).toStringAsFixed(1)}%',
            ),
            DetailValue(
              'Nguồn inference',
              text(s.ai['source'], 'Chưa khả dụng'),
            ),
            DetailValue(
              'Inference status',
              text(s.ai['inference_status'], 'Chưa khả dụng trong contract'),
            ),
          ],
        ),
        DiagnosticSection(
          title: 'HX711',
          icon: Icons.scale_outlined,
          children: [
            StatusPill(parseStatus(s.calibrationState), showCode: true),
            DetailValue('Calibration state', s.calibrationState),
            DetailValue('Raw', s.rawCounts?.toStringAsFixed(0) ?? 'null'),
            DetailValue(
              'Grams',
              s.grams == null
                  ? 'null — chưa có phép đo hợp lệ'
                  : '${s.grams!.toStringAsFixed(2)} g',
            ),
            DetailValue('Ổn định', s.stabilityState),
            DetailValue('Sample count', '${s.weightSamples ?? 'null'}'),
            DetailValue(
              'Tare / offset',
              s.tareCounts?.toStringAsFixed(2) ?? 'null',
            ),
            DetailValue(
              'Scale (g/count)',
              s.gramsPerCount?.toStringAsPrecision(8) ?? 'null',
            ),
            DetailValue(
              'Tuổi telemetry',
              s.weightAge == null
                  ? 'null'
                  : '${s.weightAge!.toStringAsFixed(2)} s',
            ),
            DetailValue(
              'Spread / sigma',
              '${number(w['spread_grams']) ?? 'null'} / ${number(w['stddev_grams']) ?? 'null'} g',
            ),
            CalibrationPanel(backend: backend),
          ],
        ),
        DiagnosticSection(
          title: 'Ultrasonic',
          icon: Icons.sensors,
          children: [
            for (final sensor in UltrasonicState.fromSystem(s))
              _UltrasonicTile(sensor),
          ],
        ),
        DiagnosticSection(
          title: 'PIR',
          icon: Icons.motion_photos_on,
          children: [
            StatusPill(parseStatus(s.health('pir')), showCode: true),
            DetailValue(
              'Chuyển động',
              s.online && s.sensor('pir')['motion'] is bool
                  ? (s.sensor('pir')['motion'] == true
                        ? 'Có chuyển động'
                        : 'Chưa phát hiện chuyển động')
                  : 'UNKNOWN',
            ),
            DetailValue(
              'Transitions',
              s.online
                  ? '${s.sensor('pir')['transition_count'] ?? 'null'}'
                  : 'null',
            ),
          ],
        ),
        DiagnosticSection(
          title: 'OLED',
          icon: Icons.monitor,
          children: [
            StatusPill(parseStatus(s.health('oled')), showCode: true),
            const DetailValue('Địa chỉ cấu hình', '0x3C'),
          ],
        ),
        DiagnosticSection(
          title: 'Button',
          icon: Icons.touch_app_outlined,
          children: [
            StatusPill(parseStatus(s.health('manual_button')), showCode: true),
            DetailValue('GPIO cấu hình', '21 · INPUT_PULLUP'),
            DetailValue(
              'Trạng thái',
              s.online && s.sensor('manual_button')['pressed'] is bool
                  ? (s.sensor('manual_button')['pressed'] == true
                        ? 'Đang nhấn'
                        : 'Đã thả')
                  : 'UNKNOWN',
            ),
            DetailValue(
              'Request count',
              s.online
                  ? '${s.sensor('manual_button')['request_count'] ?? 'null'}'
                  : 'null',
            ),
            const InfoNote(
              'Nút tạo yêu cầu qua arbiter, không gọi trực tiếp servo.',
            ),
          ],
        ),
        DiagnosticSection(
          title: 'Scheduled Worker',
          icon: Icons.schedule,
          children: [
            StatusPill(
              parseStatus(backend.scheduledWorker.status),
              label: workerStatusText(backend.scheduledWorker.status),
              showCode: true,
            ),
            DetailValue('Trạng thái worker', backend.scheduledWorker.status),
            TechnicalDetails(data: backend.scheduledWorker.data),
            const InfoNote(
              'Counter theo phiên; occurrence lưu bền nằm trong Lịch sử.',
            ),
          ],
        ),
        AutoCatPanel(state: s),
        DiagnosticSection(
          title: 'Actuator safety',
          icon: Icons.shield_outlined,
          children: [
            for (final key in [
              'servo_armed',
              'pump_armed',
              'auto_feed',
              'auto_water',
              'actuator_execution',
            ])
              _Device(
                key,
                s.safety[key] == false
                    ? AppStatus.disabled
                    : s.safety[key] == true
                    ? AppStatus.blocked
                    : AppStatus.unknown,
                label: boolText(s.safety[key]),
              ),
            DetailValue(
              'actuator_outputs_enabled',
              '${s.safety['actuator_outputs_enabled'] ?? 'UNKNOWN'}',
            ),
            DetailValue('Servo state', text(s.safety['servo_state'])),
            DetailValue('Pump state', text(s.safety['pump_state'])),
            const InfoNote(
              'DRY RUN là chế độ của ứng dụng; trạng thái GPIO/arming chỉ được xác nhận từ telemetry thật.',
            ),
          ],
        ),
        AppCard(
          child: TechnicalDetails(title: 'Snapshot SystemState', data: s.data),
        ),
      ],
    );
  }
}

class _Device extends StatelessWidget {
  final String title;
  final AppStatus status;
  final String? label;
  const _Device(this.title, this.status, {this.label});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        StatusPill(status, label: label, showCode: true),
      ],
    ),
  );
}

class _UltrasonicTile extends StatelessWidget {
  final UltrasonicState sensor;
  const _UltrasonicTile(this.sensor);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${sensor.type} #${sensor.sensorId.endsWith('1') ? '1' : '2'}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        StatusPill(sensor.state, showCode: true),
        Text('Vai trò: ${sensor.role}'),
        Text(cmText(sensor.distanceCm)),
        Text(
          sensor.ageSeconds == null
              ? 'Tuổi mẫu: Chưa có timestamp'
              : 'Tuổi mẫu: ${(sensor.ageSeconds! * 1000).toStringAsFixed(0)} ms',
        ),
        if (sensor.metadata?['firmware_supported'] == false &&
            sensor.sensorId.endsWith('2'))
          const InfoNote(
            'Firmware hiện tại chưa có kênh này — cần flash bản 4 ultrasonic.',
          ),
        if (sensor.triggerGpio != null)
          Text('Cấu hình: TRIG ${sensor.triggerGpio} / ECHO ${sensor.echoGpio}')
        else
          Text(
            'Đề xuất: TRIG ${sensor.proposedTrigger} / ECHO ${sensor.proposedEcho} · chưa áp dụng',
          ),
        if (sensor.proposedTrigger != null)
          const InfoNote(
            'Chân dự kiến có xung đột RESERVED trong checkpoint phần cứng; cần xác nhận trước khi đấu. Không chỉnh GPIO từ app.',
          ),
        TechnicalDetails(
          title: 'Schema cảm biến',
          data: {
            'sensor_id': sensor.sensorId,
            'type': sensor.type,
            'role': sensor.role,
            'enabled': sensor.enabled,
            'configured': sensor.configured,
            'wired': sensor.wired,
            'distance_cm': sensor.distanceCm,
            'valid': sensor.valid,
            'timeout': sensor.timeout,
            'stale': sensor.stale,
            'age': sensor.ageSeconds,
            'sample_age_ms': sensor.ageSeconds == null
                ? null
                : (sensor.ageSeconds! * 1000).round(),
            'last_update': sensor.lastUpdate,
            if (sensor.metadata != null) 'source': sensor.metadata,
            'state': sensor.state.code,
          },
        ),
      ],
    ),
  );
}

class CalibrationPanel extends StatelessWidget {
  final FeederBackend backend;
  const CalibrationPanel({super.key, required this.backend});
  @override
  Widget build(BuildContext context) {
    final info = backend.calibrationInfo ?? {},
        session = object((backend.calibrationInfo ?? {})['latest_session']);
    final summaries = info['point_summaries'] is List
        ? info['point_summaries'] as List
        : [];
    final results = session['validation_results'] is List
        ? session['validation_results'] as List
        : [];
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: const Text('Hiệu chuẩn cân'),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Trạng thái: ${backend.state.calibrationState}'),
              Text('Phiên: ${text(session['state'], 'Chưa có metadata')}'),
              if (backend.connectionStatus != AppStatus.online &&
                  info.isNotEmpty)
                const InfoNote(
                  'Metadata đã tải trước đó; kết nối hiện chưa xác nhận, không phải phép đo trực tiếp.',
                ),
              if (backend.calibrationError != null)
                InfoNote(backend.calibrationError!),
              if (backend.calibrationSupported == false)
                const InfoNote(
                  'Backend hiện tại chưa hỗ trợ metadata calibration.',
                ),
              for (final mass in [0, 5, 10, 20, 30, 35])
                Builder(
                  builder: (context) {
                    final captured = summaries.any(
                      (p) =>
                          object(p)['phase'] == 'fit' &&
                          object(p)['mass_g'] == mass,
                    );
                    final match = results
                        .where((r) => object(r)['reference_g'] == mass)
                        .toList();
                    final validation = match.isEmpty
                        ? <String, dynamic>{}
                        : object(match.last);
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                captured
                                    ? Icons.check_box_outlined
                                    : Icons.check_box_outline_blank,
                                size: 20,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '$mass g${mass == 0 ? ' — Tare' : ''} · ${captured ? 'Đã thu mẫu fit' : 'Chưa có mẫu được API cung cấp'}',
                                ),
                              ),
                            ],
                          ),
                          if (validation.isNotEmpty)
                            Text(
                              'Expected: $mass g · candidate: ${validation['candidate_grams'] ?? 'null'} · error: ${validation['error_g'] ?? 'null'} · stable: ${validation['stable'] ?? 'UNKNOWN'} · ${validation['passed'] == true
                                  ? 'PASS theo backend'
                                  : validation['passed'] == false
                                  ? 'FAIL theo backend'
                                  : 'Chưa kết luận'}',
                            )
                          else
                            const Text('Kết quả kiểm chứng: Chưa có dữ liệu'),
                        ],
                      ),
                    );
                  },
                ),
              const FilledButton(
                onPressed: null,
                child: Text('Bắt đầu hiệu chuẩn — Chưa khả dụng'),
              ),
              const InfoNote(
                'App hiện chỉ đọc metadata. Không có API command calibration phù hợp để gửi; các bước đặt tải được thực hiện có người thao tác qua công cụ Jetson.',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class AutoCatPanel extends StatelessWidget {
  final FeederState state;
  const AutoCatPanel({super.key, required this.state});
  @override
  Widget build(BuildContext context) {
    final view = AutoCatView.fromSystem(state);
    return DiagnosticSection(
      title: 'AUTO CAT',
      icon: Icons.psychology_outlined,
      children: [
        DetailValue('AI', state.classification),
        DetailValue('Khoảng cách', cmText(state.distance('approach'))),
        DetailValue('State', view.state),
        if (!view.supported)
          const InfoNote(
            'NOT_AVAILABLE · Backend chưa expose state AUTO_CAT riêng. Không suy ra READY_TO_REQUEST từ dữ liệu rời rạc.',
          ),
        for (final key in ['ai', 'distance', 'stable', 'cooldown', 'hx711'])
          Text(
            '${key.toUpperCase()}: ${view.checks[key] == true
                ? 'PASS'
                : view.checks[key] == false
                ? 'FAIL'
                : 'UNKNOWN'}',
          ),
        const InfoNote(
          'Luồng chuẩn bị: AUTO_CAT request qua Feed Arbiter tới DRY RUN/BLOCKED. Không khẳng định đã có request nếu backend chưa cung cấp event.',
        ),
      ],
    );
  }
}
