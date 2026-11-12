import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'history_model.dart';
import 'status_model.dart';
import 'diagnostic_models.dart';
import 'meal_plan_panel.dart';
import 'ui_widgets.dart';
import 'live_camera_panel.dart';

String nextMealText(FeederBackend b) {
  if (b.plansError != null) return 'Chưa xác nhận được lịch mới nhất';
  if (!b.plansLoaded) return 'Chưa có dữ liệu lịch';
  if (!b.mealPlans.any((p) => p.enabled)) return 'Chưa có lịch đang bật';
  final now = b.state.jetsonNow;
  if (now == null) return 'Giờ Jetson chưa được xác nhận';
  final next = nextMeal(b.mealPlans, now, b.scheduledOccurrences);
  return next == null
      ? 'Chưa có lượt đến hạn'
      : '${vnTime(next.dueUtc, date: true)} · 35 g';
}

class OverviewPage extends StatelessWidget {
  final FeederBackend backend;
  final VoidCallback onFeed, onHistory;
  const OverviewPage({
    super.key,
    required this.backend,
    required this.onFeed,
    required this.onHistory,
  });
  @override
  Widget build(BuildContext context) {
    final s = backend.state;
    final feeding = backend.historyRecords
        .where((e) => e.category == HistoryCategory.feeding)
        .toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 24),
      children: [
        Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: const BoxDecoration(
                color: Color(0xffffe5d2),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.pets, color: appOrange),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bữa ăn của MÈO',
                    style: Theme.of(context).textTheme.titleLarge
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  StatusPill(
                    backend.connectionStatus,
                    label:
                        '${backend.isMock ? 'MOCK' : 'REAL'} · ${backend.connectionStatus.label}',
                  ),
                ],
              ),
            ),
            Icon(
              backend.connectionStatus == AppStatus.online
                  ? Icons.cloud_done_outlined
                  : Icons.cloud_off_outlined,
              color: statusColor(backend.connectionStatus),
            ),
          ],
        ),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(26),
            gradient: const LinearGradient(
              colors: [Color(0xffffe5d2), Color(0xfffff4e9)],
            ),
          ),
          child: Column(
            children: [
              const Icon(Icons.pets, size: 58, color: appOrange),
              const SizedBox(height: 8),
              Text(
                switch (s.classification) {
                  'CAT' => 'Đã phát hiện mèo',
                  'DOG' => 'Phát hiện chó',
                  'NONE' => 'Chưa phát hiện mèo',
                  _ => 'AI chưa có dữ liệu',
                },
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              Text(
                '${s.classification}${s.confidence == null ? '' : ' · ${(s.confidence! * 100).toStringAsFixed(1)}%'}',
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _InventoryCard(
                state: s,
                role: 'food',
                title: 'Thức ăn dự trữ',
                icon: Icons.rice_bowl_outlined,
                color: appOrange,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _InventoryCard(
                state: s,
                role: 'water',
                title: 'Nước dự trữ',
                icon: Icons.water_drop_outlined,
                color: appBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Bữa ăn',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
              ),
              const SizedBox(height: 8),
              const Text(
                'Mục tiêu mỗi lần: 35 g',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              Text(
                s.actualDispensedGrams == null
                    ? 'Kết quả cấp: Chưa xác minh'
                    : 'Thực cấp: ${s.actualDispensedGrams!.toStringAsFixed(1)} g',
              ),
              const SizedBox(height: 8),
              Text('Lần tiếp theo: ${nextMealText(backend)}'),
              const InfoNote(
                'Lần cấp thật gần nhất: Chưa có dữ liệu trong contract hiện tại.',
              ),
              if (feeding.isNotEmpty)
                Text(
                  'Yêu cầu gần nhất: ${vnTime(feeding.first.timestamp, date: true)} · DRY RUN',
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Hệ thống',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 16,
                runSpacing: 10,
                children: [
                  _Summary('Jetson', backend.connectionStatus),
                  _Summary('ESP32', parseStatus(s.linkHealth)),
                  _Summary('AI', parseStatus(s.ai['health'])),
                  _Summary(
                    'Worker',
                    parseStatus(backend.scheduledWorker.status),
                    label: workerStatusText(backend.scheduledWorker.status),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        FeedRequestButton(backend: backend, onFeed: onFeed),
        if (backend.requestError != null && backend.canFeed)
          InfoNote(backend.requestError!),
        if (feedUnavailableReason(backend) case final reason?) InfoNote(reason),
        if (backend.connectionError != null) InfoNote(backend.connectionError!),
        const SizedBox(height: 12),
        LiveCameraPanel(key: const ValueKey('overview-live-camera'), isMock: backend.isMock,
          base: backend.isMock ? null : Uri.tryParse(backend.endpoint),
          mockClassification: s.classification),
        const SizedBox(height: 18),
        Row(
          children: [
            const Expanded(
              child: Text(
                'Hoạt động gần đây',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
              ),
            ),
            TextButton(onPressed: onHistory, child: const Text('Xem tất cả')),
          ],
        ),
        if (backend.historyRecords.isEmpty)
          InfoNote(
            backend.historyLoaded
                ? 'Chưa có bản ghi trong phạm vi API hiện tại.'
                : 'Chưa tải được lịch sử từ Jetson.',
          )
        else ...[
          if (backend.connectionStatus != AppStatus.online)
            const InfoNote(
              'Nhật ký đã tải trước đó; không phải trạng thái thời gian thực.',
            ),
          ...backend.historyRecords
              .take(3)
              .map(
                (e) => Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: HistoryTile(entry: e, technical: false),
                ),
              ),
        ],
      ],
    );
  }
}

class _InventoryCard extends StatelessWidget {
  final FeederState state;
  final String role, title;
  final IconData icon;
  final Color color;
  const _InventoryCard({
    required this.state,
    required this.role,
    required this.title,
    required this.icon,
    required this.color,
  });
  @override
  Widget build(BuildContext context) {
    final value = state.inventory(role),
        code = state.data['${role}_reservoir_sensor'];
    final status = value != null
        ? AppStatus.healthy
        : code == 'NOT_WIRED'
        ? AppStatus.notWired
        : AppStatus.unknown;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 10),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text(
            value == null ? 'Chưa có dữ liệu' : '${value.toStringAsFixed(0)}%',
            style: TextStyle(
              color: color,
              fontSize: value == null ? 16 : 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          StatusPill(status, showCode: true),
        ],
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  final String title;
  final AppStatus status;
  final String? label;
  const _Summary(this.title, this.status, {this.label});
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      StatusPill(status, label: label),
    ],
  );
}

class FeedRequestButton extends StatelessWidget {
  final FeederBackend backend;
  final VoidCallback onFeed;
  const FeedRequestButton({
    super.key,
    required this.backend,
    required this.onFeed,
  });
  @override
  Widget build(BuildContext context) => FilledButton.icon(
    onPressed: feedUnavailableReason(backend) == null ? onFeed : null,
    icon: const Icon(Icons.restaurant),
    label: Text(
      backend.feeding ? 'Đang gửi yêu cầu…' : 'Yêu cầu cho ăn 35 g — DRY RUN',
      textAlign: TextAlign.center,
    ),
    style: FilledButton.styleFrom(
      backgroundColor: appOrange,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(54),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(17)),
    ),
  );
}

String? feedUnavailableReason(FeederBackend backend) {
  if (backend.feeding) return 'Đang chờ xác nhận yêu cầu.';
  if (!backend.isMock && backend.connectionStatus != AppStatus.online) {
    return 'Chưa kết nối Jetson; chưa thể gửi yêu cầu.';
  }
  if (!backend.online) return 'ESP32 chưa có telemetry hợp lệ để gửi yêu cầu.';
  if (!backend.canFeed) {
    return backend.requestError ??
        'Chưa xác nhận trạng thái an toàn; xem tab Hệ thống.';
  }
  return null;
}

class FeedingPage extends StatelessWidget {
  final FeederBackend backend;
  final VoidCallback onFeed;
  const FeedingPage({super.key, required this.backend, required this.onFeed});
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: [
      const PageHeading('Cho ăn', subtitle: 'Mục tiêu mỗi lần: 35 g'),
      const AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            StatusPill(AppStatus.dryRun, showCode: true),
            InfoNote(
              'Yêu cầu được xét qua arbiter. Cơ cấu cấp thức ăn đang bị khóa.',
            ),
          ],
        ),
      ),
      const SizedBox(height: 14),
      FeedRequestButton(backend: backend, onFeed: onFeed),
      if (backend.requestError != null && backend.canFeed)
        InfoNote(backend.requestError!),
      if (feedUnavailableReason(backend) case final reason?) InfoNote(reason),
      if (backend.receipt != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusPill(
                  backend.receipt!.complete
                      ? AppStatus.blocked
                      : AppStatus.dryRun,
                  showCode: true,
                ),
                Text(reasonText(backend.receipt!.reason)),
                TechnicalDetails(data: backend.receipt!.data),
              ],
            ),
          ),
        ),
      const SizedBox(height: 16),
      MealPlanPanel(backend: backend, nextMealLabel: nextMealText(backend)),
      const SizedBox(height: 16),
      MealPreferencePanel(backend: backend),
    ],
  );
}

class HistoryPage extends StatefulWidget {
  final FeederBackend backend;
  const HistoryPage({super.key, required this.backend});
  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  HistoryCategory filter = HistoryCategory.all;
  @override
  Widget build(BuildContext context) {
    final b = widget.backend;
    final items = b.historyRecords
        .where((e) => filter == HistoryCategory.all || e.category == filter)
        .toList();
    final unsupported =
        filter == HistoryCategory.water ||
        filter == HistoryCategory.ai &&
            !b.historyRecords.any((e) => e.category == HistoryCategory.ai);
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
      children: [
        PageHeading('Lịch sử', subtitle: backendHistoryCaption),
        Wrap(
          spacing: 6,
          runSpacing: 4,
          children: [
            for (final category in HistoryCategory.values)
              ChoiceChip(
                label: Text(category.label),
                selected: filter == category,
                onSelected: (_) => setState(() => filter = category),
              ),
          ],
        ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () async {
              await b.refreshHistory();
              await b.refreshMealPlans();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Tải lại lịch sử'),
          ),
        ),
        if (b.historyError != null) InfoNote(b.historyError!),
        if (b.connectionStatus != AppStatus.online)
          const InfoNote(
            'Đang hiển thị các bản ghi đã tải; kết nối hiện tại chưa sẵn sàng để cập nhật.',
          ),
        if (unsupported)
          InfoNote(
            filter == HistoryCategory.water
                ? 'Chưa hỗ trợ nhật ký cấp nước trong API hiện tại.'
                : 'Backend hiện chưa expose nhật ký chuyển trạng thái AI. Trạng thái AI hiện tại ở tab Hệ thống.',
          ),
        if (items.isEmpty && !unsupported)
          InfoNote(
            b.historyLoaded
                ? 'Chưa có bản ghi thuộc bộ lọc trong phạm vi dữ liệu API.'
                : 'Chưa tải được lịch sử từ Jetson.',
          ),
        ...items.map(
          (e) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: HistoryTile(entry: e),
          ),
        ),
        const SizedBox(height: 16),
        MealPreferencePanel(backend: b),
      ],
    );
  }
}

const backendHistoryCaption =
    'Occurrence lưu bền + event backend hiện có. DRY RUN không phải lần cấp thức ăn hoàn tất.';

class HistoryTile extends StatelessWidget {
  final HistoryEntry entry;
  final bool technical;
  const HistoryTile({super.key, required this.entry, this.technical = true});
  @override
  Widget build(BuildContext context) => AppCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          vnTime(entry.timestamp, date: true),
          style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
        ),
        const SizedBox(height: 4),
        Text(entry.title, style: const TextStyle(fontWeight: FontWeight.w800)),
        if (entry.category == HistoryCategory.feeding)
          Text(
            '${entry.targetGrams?.toStringAsFixed(0) ?? 'Chưa rõ'} g · DRY RUN',
          ),
        StatusPill(
          entry.status,
          label: entry.status == AppStatus.blocked
              ? 'Bị chặn: ${reasonText(entry.reason)}'
              : entry.status.label,
        ),
        if (technical)
          TechnicalDetails(
            data: {
              'source': entry.source,
              'record_source': entry.provenance,
              ...entry.details,
            },
          ),
      ],
    ),
  );
}

class MealPreferencePanel extends StatelessWidget {
  final FeederBackend backend;
  final bool compact;
  const MealPreferencePanel({
    super.key,
    required this.backend,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final logs = backend.mealPreferenceLogs;
    final visibleLogs = compact ? logs.take(2).toList() : logs;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Phân tích Hành vi Ăn uống & Sở thích (Món A / Món B)',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
          ),
          const SizedBox(height: 8),
          const InfoNote(
            'Thuật toán chuẩn định lượng 35 g/lần:\n'
            '• Món A (LIKE): Cấp 35 g, mèo ăn hơn phân nửa (>= 18 g hoặc > 50%, ví dụ ăn hết chỉ còn 2 g => đã ăn 33 g) => Suy ra: Mèo thích ăn Món A.\n'
            '• Món B (DISLIKE): Cấp 35 g, mèo không ăn hoặc chỉ ăn rất ít (<= 5 g, ví dụ ăn 3 g hoặc 5 g => còn thừa 32 g / 30 g) => Suy ra: Mèo không thích ăn Món B.',
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              const StatusPill(
                AppStatus.healthy,
                label: 'Mèo thích ăn Món A (LIKE)',
              ),
              const StatusPill(
                AppStatus.degraded,
                label: 'Mèo không thích ăn Món B (DISLIKE)',
              ),
            ],
          ),
          if (!compact) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => backend.recordMealPreference(
                    food: 'FOOD_A',
                    startingGrams: 35.0,
                    remainingGrams: 2.0,
                  ),
                  icon: const Icon(Icons.thumb_up_alt_outlined, size: 18),
                  label: const Text('Ghi log Món A (Còn 2 g -> Ăn 33 g)'),
                ),
                OutlinedButton.icon(
                  onPressed: () => backend.recordMealPreference(
                    food: 'FOOD_B',
                    startingGrams: 35.0,
                    remainingGrams: 32.0,
                  ),
                  icon: const Icon(Icons.thumb_down_alt_outlined, size: 18),
                  label: const Text('Ghi log Món B (Còn 32 g -> Ăn 3 g)'),
                ),
                OutlinedButton.icon(
                  onPressed: () => backend.recordMealPreference(
                    food: 'FOOD_B',
                    startingGrams: 35.0,
                    remainingGrams: 30.0,
                  ),
                  icon: const Icon(Icons.thumb_down_alt_outlined, size: 18),
                  label: const Text('Ghi log Món B (Còn 30 g -> Ăn 5 g)'),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          const Text(
            'Nhật ký đánh giá sở thích thức ăn đã lưu:',
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          for (final item in visibleLogs)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: item.isLike
                      ? const Color(0xffeef8f0)
                      : item.isDislike
                      ? const Color(0xfffff4e5)
                      : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${vnTime(item.timestamp, date: true)} · ${item.foodLabel} (${item.food})',
                      style: TextStyle(
                        color: Colors.grey.shade700,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.conclusion,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Cấp: ${item.startingGrams.toStringAsFixed(0)} g · '
                      'Đã ăn: ${item.consumedGrams.toStringAsFixed(1)} g (${item.consumedRatioPct.toStringAsFixed(1)}%) · '
                      'Còn lại: ${item.remainingGrams.toStringAsFixed(1)} g',
                    ),
                    if (!compact)
                      Material(
                        type: MaterialType.transparency,
                        child: TechnicalDetails(data: item.toJson()),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
