import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/semantics.dart' show SemanticsBinding;

import 'backend_factory.dart';
import 'feeder_backend.dart';
import 'mock_backend.dart';
import 'user_pages.dart';
import 'diagnostics_page.dart';
import 'ui_widgets.dart';
import 'reservoir_cards.dart';

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
      fontFamily: 'Roboto',
      textTheme: const TextTheme(
        bodyMedium: TextStyle(height: 1.4, color: Color(0xff302b27)),
        bodySmall: TextStyle(color: Color(0xff827871)),
      ),
      dividerTheme: const DividerThemeData(
        color: Color(0xffeee8e2),
        thickness: 1,
      ),
      expansionTileTheme: const ExpansionTileThemeData(
        shape: Border(),
        collapsedShape: Border(),
      ),
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
        title: const Text('Cho ăn 35 g?'),
        content: const Text(
          'Gửi yêu cầu cho ăn tới thiết bị. Máy sẽ thực hiện khi đủ điều kiện.',
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
    key: const ValueKey('settings'),
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: [
      const PageHeading('Cài đặt', subtitle: 'Thông tin thiết bị'),
      const SizedBox(height: 12),
      ReservoirCalibrationPanel(backend: backend),
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

      const DiagnosticSection(
        title: 'Thiết bị',
        icon: Icons.memory_outlined,
        children: [
          DetailValue('Máy chủ', 'Jetson Nano'),
          DetailValue('Bộ điều khiển', 'ESP32-S3'),
        ],
      ),
      const DiagnosticSection(
        title: 'Bữa ăn',
        icon: Icons.restaurant_outlined,
        children: [
          DetailValue('Khẩu phần mục tiêu', '35 g'),
          DetailValue('Múi giờ', 'Việt Nam · UTC+7'),
        ],
      ),
      DiagnosticSection(
        title: 'Kết nối',
        icon: Icons.wifi_outlined,
        children: [
          StatusPill(backend.connectionStatus),
          const SizedBox(height: 8),
          SelectableText(
            backend.endpoint,
            style: const TextStyle(fontSize: 13, color: Color(0xff827871)),
          ),
        ],
      ),
      AppCard(
        child: TechnicalDetails(
          title: 'Thông tin kỹ thuật',
          data: {
            'data_source': backend.state.source,
            'endpoint': backend.endpoint,
            'ai': backend.state.ai,
            'safety': backend.state.safety,
          },
        ),
      ),
    ],
  );
}
