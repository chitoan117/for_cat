from pathlib import Path
r=Path(__file__).parent;p=r/'app/lib'
s=(p/'main.dart').read_text(encoding='utf-8')
s=s.replace("title: const Text('Xác nhận request DRY RUN?')", "title: const Text('Cho ăn 35 g?')")
s=s.replace("'Gửi yêu cầu MANUAL với mục tiêu 35 g qua arbiter. Chế độ hiện tại không cấp thức ăn.'", "'Gửi yêu cầu cho ăn tới thiết bị. Máy sẽ thực hiện khi đủ điều kiện.'")
s=s.replace("child: const Text('Xác nhận'),", "child: const Text('Cho ăn'),",1)
s=s.replace('      useMaterial3: true,','''      useMaterial3: true,
      fontFamily: 'Roboto',
      textTheme: const TextTheme(bodyMedium: TextStyle(height: 1.4, color: Color(0xff302b27)), bodySmall: TextStyle(color: Color(0xff827871))),
      dividerTheme: const DividerThemeData(color: Color(0xffeee8e2), thickness: 1),
      expansionTileTheme: const ExpansionTileThemeData(shape: Border(), collapsedShape: Border()),''')
start=s.index('class SettingsPage extends StatelessWidget {')
mock=s[s.index('      if (backend is MockFeederBackend)',start):s.index('      DiagnosticSection(\n        title:',s.index('      if (backend is MockFeederBackend)',start)+10)] if False else ''
# Keep the existing MOCK scenario selector, unchanged.
a=s.index('      if (backend is MockFeederBackend)',start)
b=s.index("      DiagnosticSection(\n        title: 'Kết nối thiết bị'",a)
mock=s[a:b]
settings='''class SettingsPage extends StatelessWidget {
  final FeederBackend backend;
  const SettingsPage({super.key, required this.backend});
  @override
  Widget build(BuildContext context) => ListView(
    key: const PageStorageKey('settings'),
    padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),
    children: [
      const PageHeading('Cài đặt', subtitle: 'Thông tin thiết bị'),
'''+mock+'''
      const DiagnosticSection(title: 'Thiết bị', icon: Icons.memory_outlined, children: [
        DetailValue('Máy chủ', 'Jetson Nano'),
        DetailValue('Bộ điều khiển', 'ESP32-S3'),
      ]),
      const DiagnosticSection(title: 'Bữa ăn', icon: Icons.restaurant_outlined, children: [
        DetailValue('Khẩu phần mục tiêu', '35 g'),
        DetailValue('Múi giờ', 'Việt Nam · UTC+7'),
      ]),
      DiagnosticSection(title: 'Kết nối', icon: Icons.wifi_outlined, children: [
        StatusPill(backend.connectionStatus),
        const SizedBox(height: 8),
        SelectableText(backend.endpoint, style: const TextStyle(fontSize: 13, color: Color(0xff827871))),
      ]),
      AppCard(child: TechnicalDetails(title: 'Thông tin kỹ thuật', data: {
        'data_source': backend.state.source,
        'endpoint': backend.endpoint,
        'ai': backend.state.ai,
        'safety': backend.state.safety,
      })),
    ],
  );
}
'''
s=s[:start]+settings
(p/'main.dart').write_text(s,encoding='utf-8')

s=(p/'ui_widgets.dart').read_text(encoding='utf-8')
s=s.replace("return 'Chưa có timestamp'", "return '—'")
s=s.replace('shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),','shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: Color(0xfff0eae4))),')
a=s.index('class StatusPill extends StatelessWidget {');b=s.index('class PageHeading',a)
s=s[:a]+'''class StatusPill extends StatelessWidget {
  final AppStatus status;
  final String? label;
  final bool showCode;
  const StatusPill(this.status, {super.key, this.label, this.showCode = false});
  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
    Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), decoration: BoxDecoration(color: statusColor(status).withAlpha(18), borderRadius: BorderRadius.circular(7)), child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 5, height: 5, decoration: BoxDecoration(color: statusColor(status), shape: BoxShape.circle)),
      const SizedBox(width: 5),
      Text(label ?? status.label, style: TextStyle(color: statusColor(status), fontSize: 11, fontWeight: FontWeight.w600)),
    ])),
    if (showCode) Padding(padding: const EdgeInsets.only(top: 3), child: Text(status.code, style: const TextStyle(color: Color(0xff827871), fontSize: 10))),
  ]);
}

'''+s[b:]
s=s.replace("this.title = 'Chi tiết kỹ thuật'", "this.title = 'Chi tiết'")
s=s.replace("const Text('Sao chép chi tiết')", "const Text('Sao chép')")
(p/'ui_widgets.dart').write_text(s,encoding='utf-8')

s=(p/'status_model.dart').read_text(encoding='utf-8')
changes={
"=> 'Đang kết nối'":"=> 'Đã kết nối'",
"=> 'Hoạt động bình thường'":"=> 'Bình thường'",
"=> 'Chưa rõ trạng thái'":"=> 'Chưa có dữ liệu'",
"=> 'Dữ liệu đã cũ'":"=> 'Dữ liệu cũ'",
"=> 'Không nhận được phản hồi'":"=> 'Không phản hồi'",
"=> 'Chưa hoàn tất cấu hình'":"=> 'Chưa cấu hình'",
"=> 'Hoạt động suy giảm'":"=> 'Cần kiểm tra'",
"=> 'Chờ xác nhận giờ Jetson'":"=> 'Chờ đồng bộ giờ'",
"=> 'Đang chờ arbiter'":"=> 'Đang chờ xử lý'",
}
for a,b in changes.items():s=s.replace(a,b)
s=s.replace("String reasonText(Object? code) => switch (code) {", "String reasonText(Object? code) => switch (code) {\n  'DISPATCHED_TO_ESP32_35G' => 'Đã gửi tới thiết bị',")
s=s.replace("_ => code is String ? code : 'Chưa có kết quả'", "_ => 'Chưa có kết quả'")
(p/'status_model.dart').write_text(s,encoding='utf-8')

s=(p/'diagnostics_page.dart').read_text(encoding='utf-8')
imports=s[:s.index('class DiagnosticsPage')]
legacy=s[s.index('class DiagnosticsPage'):].replace('class DiagnosticsPage extends StatelessWidget','class TechnicalDiagnostics extends StatelessWidget',1).replace('const DiagnosticsPage({','const TechnicalDiagnostics({',1)
legacy=legacy.replace("    return ListView(\n      padding: const EdgeInsets.fromLTRB(18, 20, 18, 24),", "    return ListView(\n      shrinkWrap: true,\n      physics: const NeverScrollableScrollPhysics(),\n      padding: EdgeInsets.zero,",1)
legacy=legacy.replace('  @override\n  @override','  @override')
(p/'diagnostics_page.dart').write_text(imports+(r/'diagnostics.clean.dart').read_text(encoding='utf-8')+'\n'+legacy,encoding='utf-8')

s=(p/'meal_plan_panel.dart').read_text(encoding='utf-8')
s=s.replace("const Text('Giờ Việt Nam (UTC+7) · Mục tiêu mỗi lần: 35 g')", "const Text('Giờ Việt Nam · 35 g / bữa', style: TextStyle(color: Color(0xff827871), fontSize: 12))")
s=s.replace("'Lần tiếp theo: $nextMealLabel'", "'Tiếp theo: $nextMealLabel'")
s=s.replace("'Tự xét lịch DRY RUN: ${workerStatusText(backend.scheduledWorker.status)}'", "'Lịch tự động: ${workerStatusText(backend.scheduledWorker.status)}'")
s=s.replace("'Chưa kết nối Jetson; không thể chỉnh sửa hoặc xét lịch.'", "'Chưa kết nối thiết bị để sửa lịch.'")
s=s.replace("'Chưa xác nhận danh sách lịch; tải lại trước khi chỉnh sửa.'", "'Chưa tải được lịch. Vui lòng thử lại.'")
s=s.replace("'Chưa có lịch. Lịch mới mặc định tắt.'", "'Chưa có lịch ăn.'")
s=s.replace("const Text('Chi tiết kỹ thuật')", "const Text('Chi tiết lịch')")
s=s.replace("labelText: 'Giờ HH:mm (UTC+7)'", "labelText: 'Giờ ăn (HH:mm)'")
s=s.replace("const Text('Bật lịch DRY RUN')", "const Text('Bật lịch')")
s=s.replace("subtitle: const Text(\n                'Không bật AUTO FEED hay cơ cấu cấp thức ăn.',\n              ),", "subtitle: const Text('Lịch mới mặc định tắt.'),")
s=s.replace("const Text('Mục tiêu cố định 35 g · nguồn thời gian Jetson')", "const Text('Khẩu phần 35 g · Giờ Việt Nam')")
(p/'meal_plan_panel.dart').write_text(s,encoding='utf-8')

s=(p/'live_camera_panel.dart').read_text(encoding='utf-8')
s=s.replace("CameraPhase.off => 'OFF'", "CameraPhase.off => 'Đang tắt'").replace("CameraPhase.connecting => 'CONNECTING'", "CameraPhase.connecting => 'Đang kết nối…'").replace("CameraPhase.live => 'LIVE'", "CameraPhase.live => 'Trực tiếp'").replace("CameraPhase.offline => 'OFFLINE'", "CameraPhase.offline => 'Ngoại tuyến'").replace("CameraPhase.error => 'ERROR'", "CameraPhase.error => 'Không khả dụng'")
s=s.replace("'CAMERA TRỰC TIẾP'", "'Camera'")
s=s.replace("'CAMERA_OFFLINE — chưa có nguồn frame. Không có hình camera thật.'", "'Chưa có tín hiệu camera.'")
s=s.replace("if (wanted && c?.error != null) InfoNote(c!.error!),", "if (wanted && c?.error != null) const InfoNote('Không mở được camera trên kết nối này.'),")
s=s.replace("          if (wanted)\n            const InfoNote(\n              'CAT/DOG/NONE, độ tin cậy, bbox, ROI và timestamp được gắn trong chính frame; không dùng status cũ để vẽ overlay.',\n            ),", "          if (wanted && c?.error != null) TechnicalDetails(data: {'camera_error': c!.error, 'state': phase.name}),")
s=s.replace("          if (!wanted)\n            const Text('Chỉ xem video; không phát sinh yêu cầu cho ăn.'),", '')
(p/'live_camera_panel.dart').write_text(s,encoding='utf-8')
print('Updated presentation only; transport, models, camera origin checks and device code untouched.')
