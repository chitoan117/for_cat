import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/semantics.dart' show SemanticsBinding;

import 'backend_factory.dart';
import 'feeder_backend.dart';
import 'mock_backend.dart';
import 'user_pages.dart';
import 'diagnostics_page.dart';
import 'ui_widgets.dart';
import 'feeder_state.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  if (kIsWeb) SemanticsBinding.instance.ensureSemantics();
  runApp(const FeederDemoApp());
}

class FeederDemoApp extends StatelessWidget {
  final FeederBackend? backend;
  const FeederDemoApp({super.key, this.backend});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'Bữa ăn của MÈO',
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: appOrange),
      scaffoldBackgroundColor: appCream,
    ),
    home: FeederHome(backend: backend),
  );
}

class FeederHome extends StatefulWidget {
  final FeederBackend? backend;
  const FeederHome({super.key, this.backend});
  @override
  State<FeederHome> createState() => _FeederHomeState();
}

class _FeederHomeState extends State<FeederHome> {
  int tab = 0;
  late final FeederBackend backend;
  bool confirming = false;
  @override
  void initState() {
    super.initState();
    backend = widget.backend ?? createBackend();
    backend.start();
  }

  @override
  void dispose() {
    if (widget.backend == null) backend.dispose();
    super.dispose();
  }

  Future<void> _feed() async {
    if (confirming || !backend.canFeed) return;
    confirming = true;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xác nhận request DRY RUN?'),
        content: const Text(
          'Gửi yêu cầu MANUAL với mục tiêu 35 g qua arbiter. Chế độ hiện tại không cấp thức ăn.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    confirming = false;
    if (approved == true && mounted) await backend.feed();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: backend,
    builder: (context, _) {
      final pages = <Widget>[
        OverviewPage(
          backend: backend,
          onFeed: _feed,
          onHistory: () => setState(() => tab = 2),
        ),
        FeedingPage(backend: backend, onFeed: _feed),
        HistoryPage(backend: backend),
        DiagnosticsPage(backend: backend),
        SettingsPage(backend: backend),
      ];
      return Scaffold(
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                children: [
                  if (backend.isMock)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      color: const Color(0xffffe5b2),
                      child: const Text(
                        'MOCK · Dữ liệu kiểm thử, không ghi vào Jetson',
                        style: TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                  Expanded(child: pages[tab]),
                ],
              ),
            ),
          ),
        ),
        bottomNavigationBar: _BottomNav(
          index: tab,
          onTap: (value) => setState(() => tab = value),
        ),
      );
    },
  );
}

class _BottomNav extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;
  const _BottomNav({required this.index, required this.onTap});
  @override
  Widget build(BuildContext context) {
    const items = [
      (Icons.dashboard_outlined, 'Tổng quan'),
      (Icons.restaurant_outlined, 'Cho ăn'),
      (Icons.history, 'Lịch sử'),
      (Icons.monitor_heart_outlined, 'Hệ thống'),
      (Icons.settings_outlined, 'Cài đặt'),
    ];
    return Material(
      color: Colors.white,
      child: SafeArea(
        top: false,
        child: Center(
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: SizedBox(
              height: 68,
              child: Row(
                children: [
                  for (var i = 0; i < items.length; i++)
                    Expanded(
                      child: InkWell(
                        key: ValueKey('nav_$i'),
                        onTap: () => onTap(i),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              items[i].$1,
                              color: i == index
                                  ? appOrange
                                  : const Color(0xff655b57),
                              size: 22,
                            ),
                            const SizedBox(height: 3),
                            Text(
                              items[i].$2,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 10,
                                color: i == index
                                    ? appOrange
                                    : const Color(0xff655b57),
                                fontWeight: i == index
                                    ? FontWeight.w700
                                    : FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class SettingsPage extends StatelessWidget {
  final FeederBackend backend;
  const SettingsPage({super.key, required this.backend});
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: [
      const PageHeading('Cài đặt', subtitle: 'Thông tin hệ thống · chỉ đọc'),
      if (backend is MockFeederBackend)
        DiagnosticSection(
          title: 'MOCK fixtures',
          icon: Icons.science_outlined,
          children: [
            DropdownButtonFormField<DemoScenario>(
              initialValue: (backend as MockFeederBackend).scenario,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Kịch bản kiểm thử'),
              items: DemoScenario.values
                  .map((v) => DropdownMenuItem(value: v, child: Text(v.name)))
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  (backend as MockFeederBackend).setScenario(value);
                }
              },
            ),
          ],
        ),
      DiagnosticSection(
        title: 'Kết nối thiết bị',
        icon: Icons.wifi,
        children: [
          const DetailValue('Thiết bị dự án', 'Jetson Nano · ESP32-S3'),
          DetailValue('Nguồn dữ liệu', backend.state.source),
          DetailValue('Backend endpoint', backend.endpoint),
          const InfoNote(
            'USB Serial qua C++ bridge tới backend REST/WebSocket hiện có.',
          ),
        ],
      ),
      DiagnosticSection(
        title: 'AI',
        icon: Icons.psychology_outlined,
        children: [
          const DetailValue('Runtime dự án', 'C++ OpenCV / TensorRT'),
          DetailValue(
            'Runtime source đang báo',
            text(backend.state.ai['source'], 'Chưa có metadata'),
          ),
          DetailValue(
            'YOLO model',
            text(
              backend.state.ai['model_name'],
              'Chưa có metadata model từ backend',
            ),
          ),
          DetailValue(
            'Input size',
            '${backend.state.ai['input_size'] ?? 'Chưa có metadata từ backend'}',
          ),
        ],
      ),
      DiagnosticSection(
        title: 'Cho ăn',
        icon: Icons.restaurant_outlined,
        children: [
          const DetailValue('Mục tiêu mỗi lần', '35 g'),
          DetailValue('AUTO_FEED', boolText(backend.state.safety['auto_feed'])),
          const InfoNote(
            'Lịch bật được worker xét ở DRY RUN; app không có setting mở khóa servo.',
          ),
        ],
      ),
      DiagnosticSection(
        title: 'Nước',
        icon: Icons.water_drop_outlined,
        children: [
          DetailValue(
            'AUTO_WATER',
            boolText(backend.state.safety['auto_water']),
          ),
          const InfoNote(
            'Geometry/ngưỡng nước chỉ hiện khi backend hỗ trợ. Không chỉnh GPIO từ app.',
          ),
        ],
      ),
      DiagnosticSection(
        title: 'Hệ thống',
        icon: Icons.info_outline,
        children: [
          DetailValue('REAL / MOCK', backend.state.source),
          DetailValue('Backend endpoint', backend.endpoint),
          const InfoNote(
            'Chức năng cấu hình bổ sung chưa có API sẽ không có nút chỉnh sửa.',
          ),
        ],
      ),
    ],
  );
}
