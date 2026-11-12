import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/semantics.dart' show SemanticsBinding;

import 'backend_factory.dart';
import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'mock_backend.dart';
import 'real_backend.dart';
import 'meal_plan_panel.dart';

const _orange = Color(0xffc96b3b);
const _blue = Color(0xff397fa3);
const _background = Color(0xfffffaf5);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Keep web accessibility available for touch/keyboard users and UI verification.
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
      colorScheme: ColorScheme.fromSeed(seedColor: _orange),
      scaffoldBackgroundColor: _background,
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

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: backend,
    builder: (context, _) {
      final pages = <Widget>[
        _Dashboard(
          backend: backend,
          onFeed: _feed,
          onHistory: () => setState(() => tab = 2),
        ),
        _FeedPage(backend: backend, onFeed: _feed),
        _HistoryPage(activity: backend.activity),
        _SystemPage(state: backend.state),
        _SettingsPage(backend: backend),
      ];
      return Scaffold(
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: pages[tab],
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

  Future<void> _feed() async {
    if (confirming || !backend.canFeed) return;
    confirming = true;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xác nhận request DRY RUN?'),
        content: const Text(
          'Gửi request MANUAL 35 g qua cùng arbiter. Servo/pump không chạy và không cấp thức ăn trong chế độ này.',
        ),
        actions: <Widget>[
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
    if (approved != true || !mounted) return;
    await backend.feed();
  }
}

class _Dashboard extends StatelessWidget {
  final FeederBackend backend;
  FeederState get state => backend.state;
  List<String> get activity => backend.activity;
  final VoidCallback onFeed;
  final VoidCallback onHistory;

  const _Dashboard({
    required this.backend,
    required this.onFeed,
    required this.onHistory,
  });

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 16, 18, 24),
    children: <Widget>[
      _Header(online: backend.online, source: state.source),
      const SizedBox(height: 18),
      _RecognitionCard(state: state),
      const SizedBox(height: 12),
      Row(
        children: <Widget>[
          Expanded(
            child: _MetricCard(
              icon: Icons.rice_bowl_outlined,
              value: _percent(state.inventory('food')),
              label: state.inventory('food') == null
                  ? 'Kho thức ăn · NOT_WIRED'
                  : 'Kho thức ăn',
              color: _orange,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _MetricCard(
              icon: Icons.water_drop_outlined,
              value: _percent(state.inventory('water')),
              label: state.inventory('water') == null
                  ? 'Kho nước · NOT_WIRED'
                  : 'Kho nước',
              color: _blue,
            ),
          ),
        ],
      ),
      const SizedBox(height: 12),
      _Surface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Cảm biến thật · ${state.source}',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              'Tiếp cận: ${_cm(state.distance('approach'))} · ${state.health('approach')}',
            ),
            Text(
              'Nước vận hành: ${_cm(state.distance('water_operational'))} · ${state.health('water_operational')}',
            ),
            Text(
              'Khối lượng: ${state.grams == null ? 'null · chưa hiệu chuẩn' : '${state.grams!.toStringAsFixed(1)} g'}',
            ),
            Text('HX711 raw: ${state.rawCounts?.toStringAsFixed(0) ?? 'null'}'),
          ],
        ),
      ),
      const SizedBox(height: 12),
      _Surface(
        child: Row(
          children: <Widget>[
            _CircleIcon(icon: Icons.calendar_today_outlined, color: _orange),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Hôm nay',
                    style: Theme.of(context).textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '35 g thực cấp · mục tiêu tương lai',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    'Meal Plan · ${backend.mealPlans.length} lịch cấu hình · DRY RUN',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 14),
      _FeedButton(
        feeding: backend.feeding,
        enabled: backend.canFeed,
        onPressed: onFeed,
      ),
      if (backend.connectionError != null ||
          backend.requestError != null) ...<Widget>[
        const SizedBox(height: 12),
        _Warning(text: backend.requestError ?? backend.connectionError!),
      ],
      if (backend.receipt != null) ...[
        const SizedBox(height: 12),
        _ReceiptCard(receipt: backend.receipt!),
      ],
      const SizedBox(height: 22),
      _SectionTitle(
        title: 'Hoạt động gần đây',
        action: activity.isEmpty ? null : 'Xem tất cả',
        onAction: onHistory,
      ),
      const SizedBox(height: 6),
      if (activity.isEmpty)
        const _EmptyActivity()
      else
        ...activity.take(4).map((item) => _ActivityTile(text: item)),
    ],
  );
}

class _FeedPage extends StatelessWidget {
  final FeederBackend backend;
  final VoidCallback onFeed;
  const _FeedPage({required this.backend, required this.onFeed});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(22, 36, 22, 24),
    children: <Widget>[
      const SizedBox(height: 24),
      const Center(
        child: _CircleIcon(icon: Icons.restaurant, color: _orange, size: 76),
      ),
      const SizedBox(height: 18),
      Text(
        'Yêu cầu thủ công · DRY RUN',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.headlineSmall
            ?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 8),
      const Text(
        '35 g là target. Arbiter xét request; hiện không chạy servo/pump.',
        textAlign: TextAlign.center,
      ),
      const SizedBox(height: 28),
      _FeedButton(
        feeding: backend.feeding,
        enabled: backend.canFeed,
        onPressed: onFeed,
      ),
      if (backend.receipt != null) ...<Widget>[
        const SizedBox(height: 18),
        _ReceiptCard(receipt: backend.receipt!),
      ],
      if (backend.requestError != null) ...[
        const SizedBox(height: 12),
        _Warning(text: backend.requestError!),
      ],
      const SizedBox(height: 24),
      MealPlanPanel(backend: backend),
    ],
  );
}

class _HistoryPage extends StatelessWidget {
  final List<String> activity;
  const _HistoryPage({required this.activity});

  @override
  Widget build(BuildContext context) => activity.isEmpty
      ? const Center(child: _EmptyActivity(full: true))
      : ListView(
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
          children: <Widget>[
            Text(
              'Lịch sử hoạt động',
              style: Theme.of(context).textTheme.headlineMedium
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 18),
            ...activity.map((item) => _ActivityTile(text: item, large: true)),
          ],
        );
}

class _SystemPage extends StatelessWidget {
  final FeederState state;
  const _SystemPage({required this.state});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: <Widget>[
      Text(
        'Trạng thái hệ thống',
        style: Theme.of(context).textTheme.headlineMedium
            ?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 16),
      _StatusGroup(
        title: 'Kết nối',
        icon: Icons.wifi,
        items: <String>[
          'ESP32-S3 USB|${state.linkHealth}',
          'Jetson TensorRT|${text(state.ai['health'])} · ${state.classification}',
          'Dữ liệu|${state.source}',
        ],
      ),

      _StatusGroup(
        title: 'Cảm biến',
        icon: Icons.sensors,
        items: <String>[
          'Giờ Jetson|${object(state.data['time'])['time_valid'] == true ? 'TIME_VALID' : 'TIME_INVALID'}',
          'HX711|${state.health('weight')} · raw=${state.rawCounts?.toStringAsFixed(0) ?? 'null'}',
          'Gram calibration|${state.calibrated ? 'CALIBRATED' : 'DEFERRED / NOT_CALIBRATED'}',
          'HC-SR04 #1|${_cm(state.distance('approach'))} · ${state.health('approach')}',
          'JSN #1 vận hành|${_cm(state.distance('water_operational'))} · ${state.health('water_operational')}',
          'PIR GPIO11|${state.online ? state.sensor('pir')['motion']?.toString() ?? 'UNKNOWN' : 'UNKNOWN'}',
          'OLED 0x3C|${state.health('oled')}',
          'Button GPIO21|${state.online ? state.sensor('manual_button')['pressed']?.toString() ?? 'UNKNOWN' : 'UNKNOWN'} · count=${state.online ? state.sensor('manual_button')['request_count'] ?? 'null' : 'null'}',
          'Inventory #2|NOT_WIRED · GPIO TBD',
        ],
      ),
      _StatusGroup(
        title: 'Cơ cấu',
        icon: Icons.settings_input_component,
        items: <String>[
          'Servo armed|${state.online ? state.safety['servo_armed'] ?? 'UNKNOWN' : 'UNKNOWN'}',
          'Servo state|${state.online ? text(state.safety['servo_state']) : 'UNKNOWN'}',
          'Pump armed|${state.online ? state.safety['pump_armed'] ?? 'UNKNOWN' : 'UNKNOWN'}',
          'Pump state|${state.online ? text(state.safety['pump_state']) : 'UNKNOWN'}',
          'AUTO FEED / WATER|${state.online ? '${state.safety['auto_feed']} / ${state.safety['auto_water']}' : 'UNKNOWN'}',
          'Thực thi|BLOCKED · UNATTENDED_SAFE_MODE',
        ],
      ),
    ],
  );
}

class _SettingsPage extends StatelessWidget {
  final FeederBackend backend;
  const _SettingsPage({required this.backend});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: <Widget>[
      Text(
        'Cài đặt',
        style: Theme.of(context).textTheme.headlineMedium
            ?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 16),
      if (backend is MockFeederBackend)
        _SettingsCard(
          title: 'Chế độ phát triển',
          icon: Icons.science_outlined,
          child: DropdownButtonFormField<DemoScenario>(
            initialValue: (backend as MockFeederBackend).scenario,
            decoration: const InputDecoration(
              labelText: 'Kịch bản dữ liệu mẫu',
            ),
            items: DemoScenario.values
                .map(
                  (value) => DropdownMenuItem(
                    value: value,
                    child: Text(_scenarioName(value)),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) {
                (backend as MockFeederBackend).setScenario(value);
              }
            },
          ),
        ),
      const SizedBox(height: 12),
      _SettingsCard(
        title: 'Kết nối thiết bị',
        icon: Icons.wifi,
        child: Column(
          children: <Widget>[
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.devices),
              title: Text('Nguồn dữ liệu: ${backend.state.source}'),
              subtitle: Text(
                backend is RealFeederBackend
                    ? (backend as RealFeederBackend).endpoint
                    : 'MOCK · chỉ phát triển/test',
              ),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.developer_board),
              title: const Text('Jetson Nano + ESP32-S3'),
              subtitle: const Text(
                'USB Serial → C++ bridge → cùng backend REST/WebSocket',
              ),
            ),
          ],
        ),
      ),
    ],
  );
}

class _Header extends StatelessWidget {
  final bool online;
  final String source;
  const _Header({required this.online, required this.source});

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      const _CircleIcon(icon: Icons.pets, color: _orange, size: 44),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Bữa ăn của MÈO',
              style: Theme.of(context).textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            Row(
              children: <Widget>[
                Container(
                  width: 9,
                  height: 9,
                  decoration: BoxDecoration(
                    color: online
                        ? const Color(0xff4b9b61)
                        : const Color(0xffa34b4b),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '${online ? 'Đang online' : 'Mất kết nối'} · $source',
                  style: TextStyle(
                    color: online
                        ? const Color(0xff31754b)
                        : const Color(0xffa34b4b),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      Icon(
        online ? Icons.cloud_done_outlined : Icons.cloud_off_outlined,
        color: online ? const Color(0xff31754b) : const Color(0xffa34b4b),
      ),
    ],
  );
}

class _RecognitionCard extends StatelessWidget {
  final FeederState state;
  const _RecognitionCard({required this.state});

  @override
  Widget build(BuildContext context) => Container(
    height: 190,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(26),
      gradient: const LinearGradient(
        colors: <Color>[Color(0xffffe5d2), Color(0xfffff4e9)],
      ),
    ),
    child: Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(Icons.pets, size: 58, color: _orange.withValues(alpha: 0.8)),
          const SizedBox(height: 8),
          Text(
            switch (state.classification) {
              'CAT' => 'Đã nhận diện MÈO',
              'DOG' => 'Đã nhận diện CHÓ',
              'NONE' => 'Chưa phát hiện mèo',
              _ => 'AI chưa có dữ liệu',
            },
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            state.confidence != null
                ? 'Độ tin cậy ${(state.confidence! * 100).toStringAsFixed(1)}%'
                : '${text(state.ai['health'])} · ${state.classification}',
            style: TextStyle(color: Colors.brown.shade600),
          ),
        ],
      ),
    ),
  );
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;
  const _MetricCard({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) => _Surface(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, color: color, size: 27),
        const SizedBox(height: 10),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall
              ?.copyWith(color: color, fontWeight: FontWeight.w800),
        ),
        Text(
          label,
          style: TextStyle(
            color: Colors.grey.shade700,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    ),
  );
}

class _FeedButton extends StatelessWidget {
  final bool feeding;
  final bool enabled;
  final VoidCallback onPressed;
  const _FeedButton({
    required this.feeding,
    required this.enabled,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) => FilledButton.icon(
    onPressed: feeding || !enabled ? null : onPressed,
    icon: feeding
        ? const SizedBox.square(
            dimension: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : const Icon(Icons.restaurant),
    label: Text(feeding ? 'Đang gửi request...' : 'Yêu cầu 35 g — DRY RUN'),
    style: FilledButton.styleFrom(
      backgroundColor: _orange,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(54),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(17)),
      textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
    ),
  );
}

class _BottomNav extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;
  const _BottomNav({required this.index, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = <({IconData icon, String label})>[
      (icon: Icons.dashboard_outlined, label: 'Tổng quan'),
      (icon: Icons.restaurant_outlined, label: 'Cho ăn'),
      (icon: Icons.history, label: 'Lịch sử'),
      (icon: Icons.monitor_heart_outlined, label: 'Hệ thống'),
      (icon: Icons.settings_outlined, label: 'Cài đặt'),
    ];
    return Material(
      color: Colors.white,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 68,
          child: Row(
            children: <Widget>[
              for (var i = 0; i < items.length; i++)
                Expanded(
                  child: InkWell(
                    onTap: () => onTap(i),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: <Widget>[
                        Icon(
                          items[i].icon,
                          color: i == index ? _orange : const Color(0xff655b57),
                          size: 22,
                        ),
                        const SizedBox(height: 3),
                        Text(
                          items[i].label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 10,
                            color: i == index
                                ? _orange
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
    );
  }
}

class _Surface extends StatelessWidget {
  final Widget child;
  const _Surface({required this.child});

  @override
  Widget build(BuildContext context) => Card(
    margin: EdgeInsets.zero,
    elevation: 0,
    color: Colors.white,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    child: Padding(padding: const EdgeInsets.all(16), child: child),
  );
}

class _CircleIcon extends StatelessWidget {
  final IconData icon;
  final Color color;
  final double size;
  const _CircleIcon({required this.icon, required this.color, this.size = 42});

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.13),
      shape: BoxShape.circle,
    ),
    child: Icon(icon, color: color, size: size * 0.52),
  );
}

class _SectionTitle extends StatelessWidget {
  final String title;
  final String? action;
  final VoidCallback? onAction;
  const _SectionTitle({required this.title, this.action, this.onAction});

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      Expanded(
        child: Text(
          title,
          style: Theme.of(context).textTheme.titleMedium
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
      ),
      if (action != null) TextButton(onPressed: onAction, child: Text(action!)),
    ],
  );
}

class _ActivityTile extends StatelessWidget {
  final String text;
  final bool large;
  const _ActivityTile({required this.text, this.large = false});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Row(
      children: <Widget>[
        const _CircleIcon(icon: Icons.info_outline, color: _orange, size: 34),
        const SizedBox(width: 10),
        Expanded(
          child: _Surface(
            child: Text(
              text,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
        ),
      ],
    ),
  );
}

class _EmptyActivity extends StatelessWidget {
  final bool full;
  const _EmptyActivity({this.full = false});

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.symmetric(vertical: full ? 90 : 18),
    child: Column(
      children: <Widget>[
        Icon(
          Icons.auto_awesome_outlined,
          size: 36,
          color: Colors.brown.shade300,
        ),
        const SizedBox(height: 8),
        Text(
          'Chưa có hoạt động nào',
          style: TextStyle(color: Colors.grey.shade700),
        ),
      ],
    ),
  );
}

class _Warning extends StatelessWidget {
  final String text;
  const _Warning({required this.text});

  @override
  Widget build(BuildContext context) => _Surface(
    child: Row(
      children: <Widget>[
        const Icon(Icons.warning_amber_rounded, color: Color(0xffa96d20)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              color: Color(0xff80551d),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    ),
  );
}

class _ReceiptCard extends StatelessWidget {
  final PreviewReceipt receipt;
  const _ReceiptCard({required this.receipt});

  @override
  Widget build(BuildContext context) => _Surface(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          receipt.complete ? 'DRY RUN — thực thi bị khóa' : 'Đang chờ arbiter',
          style: const TextStyle(fontWeight: FontWeight.w800, color: _orange),
        ),
        const SizedBox(height: 6),
        Text('ID: ${receipt.id}'),
        Text('MANUAL / ${receipt.request['sub_source']} · target 35 g'),
        Text('Lý do: ${receipt.reason}'),
        const Text('actuator_execution=false · actual_dispensed_grams=null'),
      ],
    ),
  );
}

class _StatusGroup extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<String> items;
  const _StatusGroup({
    required this.title,
    required this.icon,
    required this.items,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: _Surface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, color: _orange),
              const SizedBox(width: 10),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...items.map((item) {
            final parts = item.split('|');
            return ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text(parts[0]),
              subtitle: Text(
                parts[1],
                style: TextStyle(
                  color: _statusColor(parts[1]),
                  fontWeight: FontWeight.w700,
                ),
              ),
            );
          }),
        ],
      ),
    ),
  );
}

class _SettingsCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;
  const _SettingsCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) => _Surface(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(icon, color: _orange),
            const SizedBox(width: 10),
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
          ],
        ),
        const SizedBox(height: 14),
        child,
      ],
    ),
  );
}

String _scenarioName(DemoScenario value) => switch (value) {
  DemoScenario.normal => 'Bình thường',
  DemoScenario.ownerCat => 'Đã nhận diện MÈO',
  DemoScenario.feeding => 'Đang cấp thức ăn',
  DemoScenario.success => 'Request demo đã xét (DRY RUN)',
  DemoScenario.cooldown => 'Chưa đến thời gian cho ăn',
  DemoScenario.dailyLimit => 'Đạt giới hạn hôm nay',
  DemoScenario.foodEmpty => 'Hết thức ăn',
  DemoScenario.waterLow => 'Mức nước thấp',
  DemoScenario.sensorFault => 'Lỗi cảm biến',
  DemoScenario.offline => 'Mất kết nối bộ điều khiển',
};

Color _statusColor(String value) =>
    value == 'HEALTHY' || value == 'ONLINE' || value == 'TIME_VALID'
    ? const Color(0xff31754b)
    : value.contains('NOT_CALIBRATED') ||
          value.contains('DEFERRED') ||
          value.contains('BLOCKED')
    ? _orange
    : const Color(0xff655b57);

String _cm(double? value) =>
    value == null ? '— (null)' : '${value.toStringAsFixed(2)} cm';
String _percent(double? value) =>
    value == null ? '—' : '${value.toStringAsFixed(0)}%';
