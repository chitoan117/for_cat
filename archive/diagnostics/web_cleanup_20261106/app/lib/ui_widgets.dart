import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'status_model.dart';

const appOrange = Color(0xffc96b3b),
    appBlue = Color(0xff397fa3),
    appCream = Color(0xfffffaf5);
Color statusColor(AppStatus status) => switch (status) {
  AppStatus.online || AppStatus.healthy => const Color(0xff31754b),
  AppStatus.offline || AppStatus.blocked => const Color(0xffa34b4b),
  AppStatus.unknown ||
  AppStatus.notAvailable ||
  AppStatus.disabled => const Color(0xff655b57),
  _ => const Color(0xff986020),
};
String vnTime(DateTime? utc, {bool date = false}) {
  if (utc == null) return '—';
  final v = utc.toUtc().add(const Duration(hours: 7));
  final clock =
      '${v.hour.toString().padLeft(2, '0')}:${v.minute.toString().padLeft(2, '0')}';
  return date
      ? '${v.day.toString().padLeft(2, '0')}/${v.month.toString().padLeft(2, '0')} · $clock'
      : clock;
}

String boolText(Object? value) => value == true
    ? 'Bật'
    : value == false
    ? 'Tắt'
    : 'Chưa rõ';
String cmText(double? value) =>
    value == null ? 'Chưa có dữ liệu' : '${value.toStringAsFixed(2)} cm';

class AppCard extends StatelessWidget {
  final Widget child;
  const AppCard({super.key, required this.child});
  @override
  Widget build(BuildContext context) => Card(
    elevation: 0,
    margin: EdgeInsets.zero,
    color: Colors.white,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(18),
      side: const BorderSide(color: Color(0xfff0eae4)),
    ),
    child: Padding(padding: const EdgeInsets.all(16), child: child),
  );
}

class StatusPill extends StatelessWidget {
  final AppStatus status;
  final String? label;
  final bool showCode;
  const StatusPill(this.status, {super.key, this.label, this.showCode = false});
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: statusColor(status).withAlpha(18),
          borderRadius: BorderRadius.circular(7),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                color: statusColor(status),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 5),
            Flexible(
              child: Text(
                label ?? status.label,
                style: TextStyle(
                  color: statusColor(status),
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
      if (showCode)
        Padding(
          padding: const EdgeInsets.only(top: 3),
          child: Text(
            status.code,
            style: const TextStyle(color: Color(0xff827871), fontSize: 10),
          ),
        ),
    ],
  );
}

class PageHeading extends StatelessWidget {
  final String title, subtitle;
  const PageHeading(this.title, {super.key, this.subtitle = ''});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        if (subtitle.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(subtitle),
          ),
      ],
    ),
  );
}

class DiagnosticSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;
  const DiagnosticSection({
    super.key,
    required this.title,
    required this.icon,
    required this.children,
  });
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: appOrange, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 18,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    ),
  );
}

class DetailValue extends StatelessWidget {
  final String name, value;
  const DetailValue(this.name, this.value, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(name, style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
        Text(value, softWrap: true),
      ],
    ),
  );
}

class TechnicalDetails extends StatelessWidget {
  final Map<String, dynamic> data;
  final String title;
  const TechnicalDetails({
    super.key,
    required this.data,
    this.title = 'Chi tiết',
  });
  @override
  Widget build(BuildContext context) => ExpansionTile(
    tilePadding: EdgeInsets.zero,
    childrenPadding: const EdgeInsets.only(bottom: 12),
    title: Text(
      title,
      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
    ),
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: SelectableText(
          const JsonEncoder.withIndent('  ').convert(data),
          style: const TextStyle(fontSize: 12),
        ),
      ),
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: () => Clipboard.setData(
            ClipboardData(
              text: const JsonEncoder.withIndent('  ').convert(data),
            ),
          ),
          icon: const Icon(Icons.copy, size: 16),
          label: const Text('Sao chép'),
        ),
      ),
    ],
  );
}

class InfoNote extends StatelessWidget {
  final String text;
  const InfoNote(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Text(
      text,
      style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
    ),
  );
}
