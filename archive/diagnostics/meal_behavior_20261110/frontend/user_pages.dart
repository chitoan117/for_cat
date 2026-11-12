import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'history_model.dart';
import 'diagnostic_models.dart';
import 'status_model.dart';
import 'meal_plan_panel.dart';
import 'ui_widgets.dart';

String nextMealText(FeederBackend b) {
  if (b.plansError != null) return 'Chưa cập nhật được lịch';
  if (!b.plansLoaded) return 'Đang tải lịch…';
  if (!b.mealPlans.any((p) => p.enabled)) return 'Chưa đặt lịch';
  final now = b.state.jetsonNow;
  if (now == null) return 'Chưa xác nhận giờ thiết bị';
  final next = nextMeal(b.mealPlans, now, b.scheduledOccurrences);
  return next == null
      ? 'Chưa có bữa tiếp theo'
      : vnTime(next.dueUtc, date: true);
}

String animalLabel(FeederState state) => switch (state.classification) {
  'CAT' => 'Đã phát hiện mèo',
  'DOG' => 'Phát hiện chó',
  'NONE' => 'Chờ mèo tới',
  _ => 'Chưa có dữ liệu nhận diện',
};

bool requestDispatched(Object? reason) => reason == 'DISPATCHED_TO_ESP32_35G';
String requestLabel(Object? reason, AppStatus status) =>
    requestDispatched(reason)
    ? 'Đã gửi tới thiết bị'
    : status == AppStatus.blocked
    ? reasonText(reason)
    : status.label;

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
    final recent = backend.historyRecords
        .where((e) => e.title != 'Sự kiện hệ thống')
        .take(3)
        .toList();
    return ListView(
      key: const ValueKey('overview'),
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
      children: [
        Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: appOrange.withAlpha(22),
                borderRadius: BorderRadius.circular(14),
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
                  const SizedBox(height: 3),
                  StatusPill(backend.connectionStatus),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: const Color(0xffffecdd),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            children: [
              const Icon(Icons.pets, size: 38, color: appOrange),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  animalLabel(s),
                  style: const TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              if (s.confidence != null)
                Text(
                  '${(s.confidence! * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(
                    color: appOrange,
                    fontWeight: FontWeight.w700,
                  ),
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
        const SizedBox(height: 14),
        FeedRequestButton(backend: backend, onFeed: onFeed),
        if (feedUnavailableReason(backend) case final reason?) InfoNote(reason),
        if (backend.requestError != null && backend.canFeed)
          InfoNote(backend.requestError!),
        const SizedBox(height: 12),
        AppCard(
          child: Row(
            children: [
              const Icon(Icons.schedule_outlined, color: appOrange, size: 22),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Bữa tiếp theo',
                      style: TextStyle(color: Color(0xff7a716b), fontSize: 12),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      nextMealText(backend),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'Khẩu phần',
                    style: TextStyle(color: Color(0xff7a716b), fontSize: 11),
                  ),
                  Text(
                    '35 g',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
                  ),
                ],
              ),
            ],
          ),
        ),
        if (s.actualDispensedGrams != null)
          InfoNote('Đã cấp ${s.actualDispensedGrams!.toStringAsFixed(1)} g'),
        const SizedBox(height: 18),
        Row(
          children: [
            const Expanded(
              child: Text(
                'Hoạt động gần đây',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
              ),
            ),
            TextButton(onPressed: onHistory, child: const Text('Xem tất cả')),
          ],
        ),
        if (backend.connectionStatus != AppStatus.online &&
            backend.historyLoaded)
          const InfoNote('Đang hiển thị lịch sử đã lưu.'),
        if (recent.isEmpty)
          InfoNote(
            backend.historyLoaded
                ? 'Chưa có hoạt động.'
                : 'Đang tải hoạt động…',
          ),
        for (final e in recent)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: HistoryTile(entry: e, technical: false),
          ),
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
    final value = state.inventory(role);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  title,
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
          SizedBox(
            height: 18,
            child: Align(
              alignment: Alignment.centerLeft,
              child: value == null
                  ? const Text(
                      'Chưa có dữ liệu',
                      style: TextStyle(color: Color(0xff827871), fontSize: 12),
                    )
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: value / 100,
                        minHeight: 4,
                        color: color,
                        backgroundColor: color.withAlpha(20),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
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
    icon: const Icon(Icons.restaurant, size: 20),
    label: Text(
      backend.feeding ? 'Đang gửi…' : 'Cho ăn 35 g',
      textAlign: TextAlign.center,
    ),
    style: FilledButton.styleFrom(
      backgroundColor: appOrange,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(50),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
  );
}

String? feedUnavailableReason(FeederBackend backend) {
  if (backend.feeding) return 'Đang chờ xác nhận.';
  if (!backend.isMock && backend.connectionStatus != AppStatus.online) {
    return 'Chưa kết nối máy chủ.';
  }
  if (!backend.online) return 'Thiết bị chưa sẵn sàng.';
  if (!backend.canFeed) {
    return backend.requestError ?? 'Chưa thể cho ăn. Xem mục Hệ thống.';
  }
  return null;
}

class FeedingPage extends StatelessWidget {
  final FeederBackend backend;
  final VoidCallback onFeed;
  const FeedingPage({super.key, required this.backend, required this.onFeed});
  @override
  Widget build(BuildContext context) {
    final s = backend.state;
    final receipt = backend.receipt;
    final dispatched = requestDispatched(receipt?.reason);
    return ListView(
      key: const ValueKey('feeding'),
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
      children: [
        const PageHeading('Cho ăn', subtitle: 'Khẩu phần mục tiêu 35 g'),
        AppCard(
          child: Row(
            children: [
              const Icon(Icons.scale_outlined, color: appOrange, size: 26),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Khối lượng trên cân',
                      style: TextStyle(color: Color(0xff7a716b), fontSize: 12),
                    ),
                    Text(
                      s.grams == null
                          ? 'Chưa có dữ liệu'
                          : '${s.grams!.toStringAsFixed(1)} g',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 22,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        FeedRequestButton(backend: backend, onFeed: onFeed),
        if (backend.requestError != null && backend.canFeed)
          InfoNote(backend.requestError!),
        if (feedUnavailableReason(backend) case final reason?) InfoNote(reason),
        if (receipt != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StatusPill(
                    dispatched
                        ? AppStatus.online
                        : receipt.complete
                        ? AppStatus.blocked
                        : AppStatus.dryRun,
                    label: dispatched
                        ? 'Đã gửi tới thiết bị'
                        : receipt.complete
                        ? reasonText(receipt.reason)
                        : 'Đang chờ xử lý',
                  ),
                  TechnicalDetails(data: receipt.data),
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
    return ListView(
      key: const ValueKey('history'),
      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
      children: [
        const PageHeading('Lịch sử', subtitle: backendHistoryCaption),
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
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Tải lại lịch sử'),
          ),
        ),
        if (b.historyError != null) InfoNote(b.historyError!),
        if (b.connectionStatus != AppStatus.online)
          const InfoNote('Đang hiển thị lịch sử đã lưu.'),
        if (items.isEmpty && filter == HistoryCategory.water)
          const InfoNote('Chưa hỗ trợ nhật ký nước.')
        else if (items.isEmpty)
          InfoNote(
            b.historyLoaded
                ? 'Chưa có hoạt động trong mục này.'
                : 'Đang tải lịch sử…',
          ),
        for (final e in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: HistoryTile(entry: e),
          ),
        const SizedBox(height: 16),
        MealPreferencePanel(backend: b),
      ],
    );
  }
}

const backendHistoryCaption = 'Yêu cầu cho ăn và hoạt động thiết bị';

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
          style: const TextStyle(color: Color(0xff827871), fontSize: 12),
        ),
        const SizedBox(height: 6),
        Text(
          entry.title
              .replaceAll(' (LIKE)', '')
              .replaceAll(' (DISLIKE)', '')
              .replaceAll(' (MODERATE)', ''),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        if (entry.category == HistoryCategory.feeding &&
            entry.targetGrams != null)
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text(
              'Mục tiêu ${entry.targetGrams!.toStringAsFixed(0)} g',
              style: const TextStyle(color: Color(0xff827871), fontSize: 12),
            ),
          ),
        if (entry.status != AppStatus.unknown ||
            entry.category == HistoryCategory.feeding)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: StatusPill(
              requestDispatched(entry.reason) ? AppStatus.online : entry.status,
              label: requestLabel(entry.reason, entry.status),
            ),
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
    final logs = backend.mealPreferenceLogs
        .where((item) => backend.isMock || !item.id.startsWith('log_food_'))
        .toList();
    final visible = compact ? logs.take(2) : logs;
    final live = backend.state.data;
    final phase = text(live['meal_phase']);
    final elapsed = number(live['meal_elapsed_seconds']) ?? 0;
    final remain = number(live['meal_remaining_g']);
    final eaten = number(live['meal_consumed_g']);
    final canControl =
        backend.online &&
        !backend.mealObservationBusy &&
        (backend.isMock || backend.mealObservationSupported == true);
    final phaseText = switch (phase) {
      'CAPTURING' => 'Đang xác nhận khẩu phần',
      'OBSERVING' => 'Đang theo dõi · ${elapsed.toInt()} / 120 giây',
      'FINAL' => 'Đã lưu kết quả bữa ăn',
      'INVALID' => 'Chưa đủ dữ liệu cân ổn định',
      _ => 'Chọn món trước khi cho ăn',
    };
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Sở thích ăn uống',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
          ),
          if (!compact) ...[
            const SizedBox(height: 12),
            const Text(
              'Món trong hộp',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'FOOD_A', label: Text('Món A')),
                ButtonSegment(value: 'FOOD_B', label: Text('Món B')),
              ],
              selected: {backend.selectedFood},
              onSelectionChanged: canControl
                  ? (value) async {
                      await backend.setMealFood(value.first);
                    }
                  : null,
            ),
            const SizedBox(height: 6),
            const Text(
              'Đổi thức ăn trong hộp trước khi chọn món.',
              style: TextStyle(fontSize: 12, color: Color(0xff827871)),
            ),
            const SizedBox(height: 12),
            Text(
              phaseText,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            if (phase == 'OBSERVING' && eaten != null && remain != null)
              Text(
                'Đã ăn ${eaten.toStringAsFixed(1)} g · Còn ${remain.toStringAsFixed(1)} g',
              ),
            if (phase == 'OBSERVING') ...[
              const SizedBox(height: 8),
              LinearProgressIndicator(value: (elapsed / 120).clamp(0.0, 1.0)),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed:
                    canControl && live['meal_stable'] == true && elapsed >= 10
                    ? () async {
                        await backend.finishMealObservation();
                      }
                    : null,
                icon: const Icon(Icons.check),
                label: const Text('Kết thúc lượt thử'),
              ),
            ],
            if (backend.mealObservationError != null)
              InfoNote(backend.mealObservationError!),
          ],
          if (logs.isEmpty) const InfoNote('Chưa có bữa ăn được đánh giá.'),
          for (final item in visible)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: item.isLike
                      ? const Color(0xfff0f7f2)
                      : const Color(0xfffaf5ef),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${vnTime(item.timestamp, date: true)} · ${item.foodLabel}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xff827871),
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      item.isLike
                          ? 'Thích ${item.foodLabel}'
                          : item.isDislike
                          ? 'Ít ăn ${item.foodLabel}'
                          : 'Ăn mức trung bình',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      'Đã ăn ${item.consumedGrams.toStringAsFixed(1)} g · Còn ${item.remainingGrams.toStringAsFixed(1)} g',
                      style: const TextStyle(fontSize: 13),
                    ),
                    if (!compact) TechnicalDetails(data: item.toJson()),
                  ],
                ),
              ),
            ),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: const Text('Cách đánh giá', style: TextStyle(fontSize: 13)),
            children: const [
              InfoNote(
                'Theo dõi 2 phút hoặc kết thúc khi mèo ăn xong. Ăn hơn nửa khẩu phần: thích; ăn tối đa 5,5 g: ít ăn. Lượng ăn được ước tính từ cân.',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
