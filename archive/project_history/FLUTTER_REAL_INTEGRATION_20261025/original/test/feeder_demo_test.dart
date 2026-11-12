import 'package:feeder_demo/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('dashboard shows feeder information at mobile width', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const FeederDemoApp());

    expect(find.text('Bữa ăn của MÈO'), findsOneWidget);
    expect(find.text('Đang online'), findsOneWidget);
    expect(find.text('Chưa phát hiện mèo'), findsOneWidget);
    expect(find.text('75%'), findsOneWidget);
    expect(find.text('82%'), findsOneWidget);
    expect(find.text('Cho ăn 40 g'), findsOneWidget);
    expect(find.text('Hoạt động gần đây'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual feed requires confirmation', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const FeederDemoApp());
    await tester.tap(find.text('Cho ăn 40 g'));
    await tester.pumpAndSettle();

    expect(find.text('Xác nhận cho ăn?'), findsOneWidget);
    expect(find.text('Hủy'), findsOneWidget);
    expect(find.text('Xác nhận'), findsOneWidget);

    await tester.tap(find.text('Hủy'));
    await tester.pumpAndSettle();
    expect(find.text('Xác nhận cho ăn?'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
