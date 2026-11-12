from pathlib import Path
r=Path(__file__).parent/'app/test'
# UI wording/navigation changed; transport/model tests and model assertions stay unchanged.
for name in ['feeder_demo_test.dart','user_app_offline_test.dart','scheduled_worker_test.dart','live_camera_test.dart']:
 p=r/name;s=p.read_text(encoding='utf-8')
 changes={
  'Yêu cầu cho ăn 35 g — DRY RUN':'Cho ăn 35 g',
  'Xác nhận request DRY RUN?':'Cho ăn 35 g?',
  "find.text('Xác nhận')":"find.text('Cho ăn')",
  "find.text('Chưa phát hiện mèo')":"find.text('Chờ mèo tới')",
  "find.text('AI chưa có dữ liệu')":"find.text('Chưa có dữ liệu nhận diện')",
  'Phân tích Hành vi Ăn uống & Sở thích (Món A / Món B)':'Sở thích ăn uống',
  "find.text('Mèo thích ăn Món A (LIKE)')":"find.text('Thích Món A')",
  "find.text('Mèo không thích ăn Món B (DISLIKE)')":"find.text('Ít ăn Món B')",
  'Cấp: 35 g · Đã ăn: 33.0 g (94.3%) · Còn lại: 2.0 g':'Đã ăn 33.0 g · Còn 2.0 g',
  'Cấp: 35 g · Đã ăn: 3.0 g (8.6%) · Còn lại: 32.0 g':'Đã ăn 3.0 g · Còn 32.0 g',
  'Chưa kết nối Jetson; không thể chỉnh sửa':'Chưa kết nối thiết bị để sửa lịch.',
  'Chưa kết nối Jetson; chưa thể gửi yêu cầu.':'Chưa kết nối máy chủ.',
  'Chờ xác nhận giờ Jetson':'Chờ đồng bộ giờ',
  'Tự xét lịch DRY RUN:':'Lịch tự động:',
  'Sao chép chi tiết':'Sao chép',
  'Thực cấp: 35.4 g':'Đã cấp 35.4 g',
  'Chưa hỗ trợ nhật ký cấp nước':'Chưa hỗ trợ nhật ký nước.',
  'LIVE · SIMULATED':'Trực tiếp · SIMULATED',
  'OFF · SIMULATED':'Đang tắt · SIMULATED',
  "find.textContaining('CAMERA_OFFLINE')":"find.textContaining('Chưa có tín hiệu camera.')",
 }
 for a,b in changes.items():s=s.replace(a,b)
 if name=='scheduled_worker_test.dart':s=s.replace("find.text('Chi tiết kỹ thuật')","find.text('Chi tiết lịch')")
 if name=='user_app_offline_test.dart':
  # The first expansion is schedule details; the receipt's expansion is now simply Details.
  s=s.replace("find.text('Chi tiết kỹ thuật')","find.text('Chi tiết lịch')",2)
  s=s.replace("find.text('Chi tiết kỹ thuật')","find.text('Chi tiết')")
  marker="    await tester.pumpWidget(FeederDemoApp(backend: backend));\n    await tester.scrollUntilVisible(\n      find.text('Chờ đồng bộ giờ')"
  s=s.replace(marker,"    await tester.pumpWidget(FeederDemoApp(backend: backend));\n    await tester.tap(find.byKey(const ValueKey('nav_3')));\n    await tester.pumpAndSettle();\n    await tester.scrollUntilVisible(\n      find.text('Chờ đồng bộ giờ')")
  s=s.replace("await tester.scrollUntilVisible(find.text('Mục tiêu mỗi lần: 35 g'), 200);\n    expect(find.text('Kết quả cấp: Chưa xác minh'), findsOneWidget);", "await tester.scrollUntilVisible(find.text('Khẩu phần'), 200);\n    expect(find.text('35 g'), findsOneWidget);\n    expect(find.textContaining('Đã cấp'), findsNothing);")
  marker="      await tester.scrollUntilVisible(\n        find.text('Hiệu chuẩn cân'),"
  s=s.replace(marker,"      await tester.scrollUntilVisible(find.text('Chẩn đoán kỹ thuật'), 250);\n      await tester.tap(find.text('Chẩn đoán kỹ thuật'));\n      await tester.pumpAndSettle();\n"+marker)
  s=s.replace("find.text('AUTO_WATER')", "find.text('Thông tin kỹ thuật')")
 p.write_text(s,encoding='utf-8')
print('Updated existing UI assertions for concise labels and collapsed diagnostics; no model/transport logic changed.')
