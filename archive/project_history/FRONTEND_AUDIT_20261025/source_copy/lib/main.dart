import 'package:flutter/material.dart';
import 'mock_backend.dart';

const _orange = Color(0xffc96b3b);
const _blue = Color(0xff397fa3);
const _background = Color(0xfffffaf5);

void main() => runApp(const FeederDemoApp());

class FeederDemoApp extends StatelessWidget {
  const FeederDemoApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'Bữa ăn của MÈO',
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: _orange),
      scaffoldBackgroundColor: _background,
    ),
    home: const FeederHome(),
  );
}

class FeederHome extends StatefulWidget {
  const FeederHome({super.key});

  @override
  State<FeederHome> createState() => _FeederHomeState();
}

class _FeederHomeState extends State<FeederHome> {
  int tab = 0;
  final MockFeederBackend backend = MockFeederBackend();

  @override
  void dispose() {
    backend.dispose();
    super.dispose();
  }

@override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: backend,
    builder: (context, _) {
      final pages = <Widget>[
        _Dashboard(
          scenario: backend.scenario,
          online: backend.online,
          feeding: backend.feeding,
          activity: backend.activity,
          onFeed: _feed,
          onHistory: () => setState(() => tab = 2),
        ),
        _FeedPage(
          feeding: backend.feeding,
          scenario: backend.scenario,
          onFeed: _feed,
        ),
        _HistoryPage(activity: backend.activity),
        _SystemPage(scenario: backend.scenario, online: backend.online),
        _SettingsPage(
          scenario: backend.scenario,
          onScenarioChanged: backend.setScenario,
        ),
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
    if (backend.feeding || !backend.online) return;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xác nhận cho ăn?'),
        content: const Text(
          'Thiết bị sẽ kiểm tra điều kiện an toàn trước khi cấp thức ăn.',
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
    if (approved != true || !mounted) return;
    await backend.feed();
  }
}

class _Dashboard extends StatelessWidget {
  final DemoScenario scenario;
  final bool online;
  final bool feeding;
  final List<String> activity;
  final VoidCallback onFeed;
  final VoidCallback onHistory;

  const _Dashboard({
    required this.scenario,
    required this.online,
    required this.feeding,
    required this.activity,
    required this.onFeed,
    required this.onHistory,
  });

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 16, 18, 24),
    children: <Widget>[
      _Header(online: online),
      const SizedBox(height: 18),
      _RecognitionCard(scenario: scenario),
      const SizedBox(height: 12),
      Row(
        children: <Widget>[
          Expanded(
            child: _MetricCard(
              icon: Icons.rice_bowl_outlined,
              value: scenario == DemoScenario.foodEmpty ? '0%' : '75%',
              label: 'Thức ăn',
              color: _orange,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _MetricCard(
              icon: Icons.water_drop_outlined,
              value: scenario == DemoScenario.waterLow ? '12%' : '82%',
              label: 'Nước',
              color: _blue,
            ),
          ),
        ],
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
                    activity.isEmpty ? '1/3 bữa' : '2/3 bữa',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    activity.isEmpty
                        ? 'Chưa có lần cho ăn hôm nay'
                        : activity.first,
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 14),
      _FeedButton(feeding: feeding, enabled: online, onPressed: onFeed),
      if (_warning(scenario) != null) ...<Widget>[
        const SizedBox(height: 12),
        _Warning(text: _warning(scenario)!),
      ],
      const SizedBox(height: 12),
      _FeedButton(feeding: feeding, enabled: online, onPressed: onFeed),
      if (_warning(scenario) != null) ...<Widget>[
        const SizedBox(height: 12),
        _Warning(text: _warning(scenario)!),
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
  final bool feeding;
  final DemoScenario scenario;
  final VoidCallback onFeed;
  const _FeedPage({
    required this.feeding,
    required this.scenario,
    required this.onFeed,
  });

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
        'Cho ăn thủ công',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.headlineSmall
            ?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 8),
      const Text(
        'Yêu cầu sẽ được kiểm tra an toàn trước khi cấp thức ăn.',
        textAlign: TextAlign.center,
      ),
      const SizedBox(height: 28),
      _FeedButton(
        feeding: feeding,
        enabled: scenario != DemoScenario.offline,
        onPressed: onFeed,
      ),
      if (scenario == DemoScenario.success) ...<Widget>[
        const SizedBox(height: 18),
        const _Result(text: 'Đã cấp thức ăn thành công', good: true),
      ],
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
  final DemoScenario scenario;
  final bool online;
  const _SystemPage({required this.scenario, required this.online});

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
          'Thiết bị AI/IoT|${online ? 'Hoạt động tốt' : 'Mất kết nối'}',
        'STM32|${online ? 'Hoạt động tốt' : 'Mất kết nối'}',
        ],
      ),

_StatusGroup(
        title: 'Cảm biến',
        icon: Icons.sensors,
        items: <String>[
          'RTC|Hoạt động tốt',
          'Cân thức ăn|${scenario == DemoScenario.sensorFault ? 'Lỗi' : 'Hoạt động tốt'}',
          'Mức nước|${scenario == DemoScenario.waterLow ? '12%' : '82%'}',
        ],
      ),
      _StatusGroup(
        title: 'Cơ cấu',
        icon: Icons.settings_input_component,
        items: <String>[
          'Servo|Hoạt động tốt',
          'Bơm|${scenario == DemoScenario.waterLow ? 'Đang kiểm tra' : 'Hoạt động tốt'}',
        ],
      ),
    ],
  );
}

class _SettingsPage extends StatelessWidget {
  final DemoScenario scenario;
  final ValueChanged<DemoScenario> onScenarioChanged;
  const _SettingsPage({
    required this.scenario,
    required this.onScenarioChanged,
  });

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
      _SettingsCard(
        title: 'Chế độ phát triển',
        icon: Icons.science_outlined,
        child: DropdownButtonFormField<DemoScenario>(
          initialValue: scenario,
          decoration: const InputDecoration(labelText: 'Kịch bản dữ liệu mẫu'),
          items: DemoScenario.values
              .map(
                (value) => DropdownMenuItem(
                  value: value,
                  child: Text(_scenarioName(value)),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) onScenarioChanged(value);
          },
        ),
      ),
      const SizedBox(height: 12),
      _SettingsCard(
        title: 'Kết nối thiết bị',
        icon: Icons.wifi,
        child: const Column(
          children: <Widget>[
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.devices),
              title: Text('ESP32-CAM'),
              subtitle: Text('Dữ liệu mock đang hoạt động'),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.developer_board),
              title: Text('STM32'),
              subtitle: Text('Điều khiển khẩu phần và an toàn'),
            ),
          ],
        ),
      ),
    ],
  );
}

class _Header extends StatelessWidget {
  final bool online;
  const _Header({required this.online});

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
                  online ? 'Đang online' : 'Mất kết nối',
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
  final DemoScenario scenario;
  const _RecognitionCard({required this.scenario});

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
            _recognition(scenario),
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            scenario == DemoScenario.ownerCat
                ? 'Độ tin cậy 94%'
                : 'Camera sẽ hiển thị ảnh tại đây',
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
    label: Text(feeding ? 'Đang cấp thức ăn...' : 'Cho ăn 40 g'),
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
                      mainAxisAlignment: 
  MainAxisAlignment.center,
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
        const _CircleIcon(
          icon: Icons.check,
          color: Color(0xff31754b),
          size: 34,
        ),
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

class _Result extends StatelessWidget {
  final String text;
  final bool good;
  const _Result({required this.text, required this.good});

  @override
  Widget build(BuildContext context) => _Surface(
    child: Row(
      children: <Widget>[
        Icon(
          good ? Icons.check_circle_outline : Icons.info_outline,
          color: good ? const Color(0xff31754b) : _orange,
        ),
        const SizedBox(width: 10),
        Text(text, style: const TextStyle(fontWeight: FontWeight.w700)),
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
              trailing: Text(
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
String _recognition(DemoScenario value) => switch (value) {
  DemoScenario.ownerCat => 'Đã nhận diện MÈO'
  DemoScenario.offline => 'Chưa kết nối camera',
  _ => 'Chưa phát hiện mèo',
};

String? _warning(DemoScenario value) => switch (value) {
  DemoScenario.cooldown => 'Chưa đến thời gian cho ăn tiếp',
  DemoScenario.dailyLimit => 'Đã đạt giới hạn khẩu phần hôm nay',
  DemoScenario.foodEmpty => 'Thức ăn trong thùng đã hết',
  DemoScenario.waterLow => 'Mức nước thấp',
  DemoScenario.sensorFault => 'Cảm biến cần được kiểm tra',
  DemoScenario.offline => 'Bộ điều khiển đang mất kết nối',
  _ => null,
};

String _scenarioName(DemoScenario value) => switch (value) {
  DemoScenario.ownerCat => 'Bình thường',
  DemoScenario.ownerCat => 'Đã nhận diện MÈO',
  DemoScenario.feeding => 'Đang cấp thức ăn',
  DemoScenario.success => 'Cấp thức ăn thành công',
  DemoScenario.cooldown => 'Chưa đến thời gian cho ăn',
  DemoScenario.dailyLimit => 'Đạt giới hạn hôm nay',
  DemoScenario.foodEmpty => 'Hết thức ăn',
  DemoScenario.waterLow => 'Mức nước thấp',
  DemoScenario.sensorFault => 'Lỗi cảm biến',
  DemoScenario.offline => 'Mất kết nối bộ điều khiển',
};

Color _statusColor(String value) =>
    value == 'Hoạt động tốt' || value.contains('%') || value == 'Đang kiểm tra'
    ? const Color(0xff31754b)
    : const Color(0xffa34b4b);
