import 'package:flutter/material.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'meal_plans.dart';
import 'status_model.dart';
import 'ui_widgets.dart';

const _dayLabels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];

class MealPlanPanel extends StatelessWidget {
  final FeederBackend backend;
  final String? nextMealLabel;
  const MealPlanPanel({super.key, required this.backend, this.nextMealLabel});
  Future<void> _edit(BuildContext context, [MealPlan? plan]) async {
    final draft = await showDialog<_PlanDraft>(
      context: context,
      builder: (_) => _PlanEditor(plan: plan),
    );
    if (draft != null && context.mounted) {
      await backend.saveMealPlan(
        existing: plan,
        name: draft.name,
        localTime: draft.time,
        weekdays: draft.days,
        enabled: draft.enabled,
      );
    }
  }

  Future<void> _delete(BuildContext context, MealPlan plan) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xóa lịch?'),
        content: Text(plan.name),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xóa lịch'),
          ),
        ],
      ),
    );
    if (ok == true) await backend.deleteMealPlan(plan);
  }

  @override
  Widget build(BuildContext context) {
    final canChangePlans =
        !backend.isMock &&
        backend.connectionStatus == AppStatus.online &&
        backend.plansLoaded &&
        backend.plansError == null &&
        !backend.plansBusy;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Lịch ăn',
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          const Text('Giờ Việt Nam (UTC+7) · Mục tiêu mỗi lần: 35 g'),
          if (nextMealLabel != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Lần tiếp theo: $nextMealLabel',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          if (backend.isMock)
            const InfoNote(
              'MOCK · cấu hình lịch thử nghiệm, không ghi vào Jetson.',
            )
          else ...[
            InfoNote(
              'Tự xét lịch DRY RUN: ${workerStatusText(backend.scheduledWorker.status)}',
            ),
            if (backend.connectionStatus != AppStatus.online)
              const InfoNote(
                'Chưa kết nối Jetson; không thể chỉnh sửa hoặc xét lịch.',
              )
            else if (!backend.plansLoaded || backend.plansError != null)
              const InfoNote(
                'Chưa xác nhận danh sách lịch; tải lại trước khi chỉnh sửa.',
              ),
            Wrap(
              spacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: canChangePlans ? () => _edit(context) : null,
                  icon: const Icon(Icons.add),
                  label: const Text('Thêm lịch'),
                ),
                TextButton.icon(
                  onPressed: backend.plansBusy
                      ? null
                      : backend.refreshMealPlans,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Tải lại lịch'),
                ),
              ],
            ),
            if (backend.plansBusy)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: LinearProgressIndicator(),
              ),
            if (backend.plansError != null) InfoNote(backend.plansError!),
            if (backend.mealPlans.isEmpty &&
                !backend.plansBusy &&
                backend.plansError == null)
              const InfoNote('Chưa có lịch. Lịch mới mặc định tắt.'),
          ],
          for (final plan in backend.mealPlans) ...[
            const Divider(height: 24),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${plan.name} · ${plan.localTime}',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      Text(
                        '${plan.weekdays.map((d) => _dayLabels[d]).join(', ')} · ${plan.enabled ? 'Đang bật' : 'Đang tắt'}',
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: plan.enabled,
                  onChanged: canChangePlans
                      ? (value) => backend.saveMealPlan(
                          existing: plan,
                          name: plan.name,
                          localTime: plan.localTime,
                          weekdays: plan.weekdays,
                          enabled: value,
                        )
                      : null,
                ),
              ],
            ),
            Wrap(
              spacing: 8,
              children: [
                TextButton(
                  onPressed: canChangePlans ? () => _edit(context, plan) : null,
                  child: const Text('Sửa'),
                ),
                TextButton(
                  onPressed: canChangePlans
                      ? () => _delete(context, plan)
                      : null,
                  child: const Text('Xóa'),
                ),
              ],
            ),
          ],
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: const Text('Chi tiết kỹ thuật'),
            children: [
              if (!canChangePlans)
                const InfoNote(
                  'Xét lịch chỉ khả dụng khi kết nối REAL và danh sách lịch đã tải.',
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Scheduled Worker · ${backend.scheduledWorker.status}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const InfoNote(
                      'SCHEDULED · DRY RUN. Cửa sổ đến hạn 60 giây; không truy lĩnh. Mỗi lịch tối đa một occurrence/ngày.',
                    ),
                    for (final key in [
                      'last_poll_at',
                      'submitted_count',
                      'error_count',
                      'last_error',
                    ])
                      DetailValue(
                        key,
                        '${backend.scheduledWorker.data[key] ?? 'UNKNOWN'}',
                      ),
                    for (final plan in backend.mealPlans) ...[
                      Text(
                        plan.name,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      OutlinedButton(
                        onPressed: canChangePlans
                            ? () => backend.previewMealPlan(plan)
                            : null,
                        child: const Text('Xét lịch — DRY RUN'),
                      ),
                      TechnicalDetails(
                        title: 'Cấu hình lịch / ID',
                        data: {
                          'plan_id': plan.id,
                          'revision': plan.revision,
                          ...plan.definition,
                        },
                      ),
                    ],
                    if (backend.schedulePreview != null) ...[
                      Text(
                        'Kết quả xét lịch: ${reasonText(backend.schedulePreview!.reason)}',
                      ),
                      TechnicalDetails(
                        data: {
                          ...backend.schedulePreview!.data,
                          if (backend.scheduledReceipt != null)
                            'receipt': backend.scheduledReceipt!.data,
                        },
                      ),
                    ],
                    if (backend.scheduledOccurrences.isNotEmpty)
                      const Text(
                        'Occurrence đã lưu · DRY RUN',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    for (final item in backend.scheduledOccurrences.take(
                      5,
                    )) ...[
                      const Divider(),
                      Text(
                        '${item['local_date']} · ${item['origin'] == 'WORKER' ? 'Tự động' : 'Preview'} · 35 g',
                      ),
                      Text(
                        item['decision'] == null
                            ? 'Chờ arbiter'
                            : reasonText(
                                object(
                                  item['decision'],
                                )['qualification_reason'],
                              ),
                      ),
                      TechnicalDetails(
                        title: 'Occurrence / request ID',
                        data: item,
                      ),
                    ],
                    const InfoNote(
                      'actuator_execution=false · actual_dispensed_grams=null',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PlanDraft {
  final String name, time;
  final List<int> days;
  final bool enabled;
  const _PlanDraft(this.name, this.time, this.days, this.enabled);
}

class _PlanEditor extends StatefulWidget {
  final MealPlan? plan;
  const _PlanEditor({this.plan});
  @override
  State<_PlanEditor> createState() => _PlanEditorState();
}

class _PlanEditorState extends State<_PlanEditor> {
  final form = GlobalKey<FormState>();
  late final TextEditingController name, time;
  late final Set<int> days;
  late bool enabled;
  @override
  void initState() {
    super.initState();
    name = TextEditingController(text: widget.plan?.name ?? '');
    time = TextEditingController(text: widget.plan?.localTime ?? '07:00');
    days = (widget.plan?.weekdays ?? [0, 1, 2, 3, 4, 5, 6]).toSet();
    enabled = widget.plan?.enabled ?? false;
  }

  @override
  void dispose() {
    name.dispose();
    time.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    scrollable: true,
    title: Text(widget.plan == null ? 'Thêm lịch 35 g' : 'Sửa lịch 35 g'),
    content: SizedBox(
      width: 400,
      child: Form(
        key: form,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              controller: name,
              maxLength: 64,
              decoration: const InputDecoration(labelText: 'Tên lịch'),
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'Nhập tên lịch' : null,
            ),
            TextFormField(
              controller: time,
              keyboardType: TextInputType.datetime,
              decoration: const InputDecoration(labelText: 'Giờ HH:mm (UTC+7)'),
              validator: (v) =>
                  v != null &&
                      RegExp(r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$').hasMatch(v)
                  ? null
                  : 'Nhập giờ từ 00:00 đến 23:59',
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 4,
              children: [
                for (var day = 0; day < 7; day++)
                  FilterChip(
                    label: Text(_dayLabels[day]),
                    selected: days.contains(day),
                    onSelected: (selected) => setState(() {
                      if (selected) {
                        days.add(day);
                      } else {
                        days.remove(day);
                      }
                    }),
                  ),
              ],
            ),
            if (days.isEmpty)
              const Text(
                'Chọn ít nhất một ngày',
                style: TextStyle(color: Colors.red),
              ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Bật lịch DRY RUN'),
              subtitle: const Text(
                'Không bật AUTO FEED hay cơ cấu cấp thức ăn.',
              ),
              value: enabled,
              onChanged: (v) => setState(() => enabled = v),
            ),
            const Text('Mục tiêu cố định 35 g · nguồn thời gian Jetson'),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Hủy'),
      ),
      FilledButton(
        onPressed: () {
          if (form.currentState!.validate() && days.isNotEmpty) {
            Navigator.pop(
              context,
              _PlanDraft(
                name.text.trim(),
                time.text,
                days.toList()..sort(),
                enabled,
              ),
            );
          }
        },
        child: const Text('Lưu lịch'),
      ),
    ],
  );
}
