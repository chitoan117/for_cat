import 'package:feeder_demo/main.dart';
import 'package:feeder_demo/mock_backend.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('dashboard shows feeder information at mobile width', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final backend = MockFeederBackend(); addTearDown(backend.dispose);
    await tester.pumpWidget(FeederDemoApp(backend: backend));

    expect(find.text('Bữa ăn của MÈO'), findsOneWidget);
    expect(find.text('Đang online · MOCK'), findsOneWidget);
    expect(find.text('Chưa phát hiện mèo'), findsOneWidget);
    expect(find.text('75%'), findsOneWidget);
    expect(find.text('82%'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Yêu cầu 35 g — DRY RUN'), 200);
    expect(find.text('Yêu cầu 35 g — DRY RUN'), findsOneWidget);
    expect(find.text('Hoạt động gần đây'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual feed requires confirmation', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final backend = MockFeederBackend(); addTearDown(backend.dispose);
    await tester.pumpWidget(FeederDemoApp(backend: backend));
    await tester.scrollUntilVisible(find.text('Yêu cầu 35 g — DRY RUN'), 200);
    await tester.tap(find.text('Yêu cầu 35 g — DRY RUN'));
    await tester.pumpAndSettle();

    expect(find.text('Xác nhận request DRY RUN?'), findsOneWidget);
    expect(find.text('Hủy'), findsOneWidget);
    expect(find.text('Xác nhận'), findsOneWidget);

    await tester.tap(find.text('Hủy'));
    await tester.pumpAndSettle();
    expect(find.text('Xác nhận request DRY RUN?'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('default REAL starts unknown, never shows mock percentages or meal counts', (tester) async {
    tester.view.physicalSize = const Size(390, 844); tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(const FeederDemoApp()); await tester.pump();
    expect(find.text('75%'), findsNothing); expect(find.text('82%'), findsNothing);
    expect(find.text('1/3 bữa'), findsNothing); expect(find.text('Cho ăn 40 g'), findsNothing);
    expect(find.text('AI chưa có dữ liệu'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
