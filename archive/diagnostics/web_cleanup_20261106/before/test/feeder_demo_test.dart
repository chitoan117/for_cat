import 'package:feeder_demo/history_model.dart';
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

    final backend = MockFeederBackend();
    addTearDown(backend.dispose);
    await tester.pumpWidget(FeederDemoApp(backend: backend));

    expect(find.text('Bữa ăn của MÈO'), findsOneWidget);
    expect(find.textContaining('MOCK · Dữ liệu kiểm thử'), findsOneWidget);
    expect(find.text('Chưa phát hiện mèo'), findsOneWidget);
    expect(find.text('75%'), findsOneWidget);
    expect(find.text('82%'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Yêu cầu cho ăn 35 g — DRY RUN'),
      200,
    );
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -180));
    await tester.pumpAndSettle();
    expect(find.text('Yêu cầu cho ăn 35 g — DRY RUN'), findsOneWidget);
    expect(find.text('Hoạt động gần đây'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual feed requires confirmation', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final backend = MockFeederBackend();
    addTearDown(backend.dispose);
    await tester.pumpWidget(FeederDemoApp(backend: backend));
    await tester.scrollUntilVisible(
      find.text('Yêu cầu cho ăn 35 g — DRY RUN'),
      200,
    );
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -180));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yêu cầu cho ăn 35 g — DRY RUN'));
    await tester.pumpAndSettle();

    expect(find.text('Xác nhận request DRY RUN?'), findsOneWidget);
    expect(find.text('Hủy'), findsOneWidget);
    expect(find.text('Xác nhận'), findsOneWidget);

    await tester.tap(find.text('Hủy'));
    await tester.pumpAndSettle();
    expect(find.text('Xác nhận request DRY RUN?'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'default REAL starts unknown, never shows mock percentages or meal counts',
    (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(const FeederDemoApp());
      await tester.pump();
      expect(find.text('75%'), findsNothing);
      expect(find.text('82%'), findsNothing);
      expect(find.text('1/3 bữa'), findsNothing);
      expect(find.text('Cho ăn 40 g'), findsNothing);
      expect(find.text('AI chưa có dữ liệu'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'evaluateMealPreference classifies Mon A LIKE (>50% or remaining 2g) and Mon B DISLIKE (0-5g eaten / remaining 30-35g)',
    () {
      // Món A: Cấp 35g, còn 2g -> ăn 33g => LIKE
      final monA2g = evaluateMealPreference(
        food: 'FOOD_A',
        startingGrams: 35.0,
        remainingGrams: 2.0,
      );
      expect(monA2g.food, 'FOOD_A');
      expect(monA2g.consumedGrams, 33.0);
      expect(monA2g.preference, 'LIKE');
      expect(monA2g.conclusion, 'Mèo thích ăn Món A (LIKE)');

      // Món A: Cấp 35g, ăn hơn phân nửa (ăn 19g, còn 16g) => LIKE
      final monAHalf = evaluateMealPreference(
        food: 'FOOD_A',
        startingGrams: 35.0,
        remainingGrams: 16.0,
      );
      expect(monAHalf.consumedGrams, 19.0);
      expect(monAHalf.preference, 'LIKE');
      expect(monAHalf.conclusion, 'Mèo thích ăn Món A (LIKE)');

      // Món B: Cấp 35g, ăn 3g, còn 32g => DISLIKE
      final monB3g = evaluateMealPreference(
        food: 'FOOD_B',
        startingGrams: 35.0,
        remainingGrams: 32.0,
      );
      expect(monB3g.food, 'FOOD_B');
      expect(monB3g.consumedGrams, 3.0);
      expect(monB3g.preference, 'DISLIKE');
      expect(monB3g.conclusion, 'Mèo không thích ăn Món B (DISLIKE)');

      // Món B: Cấp 35g, ăn 5g, còn 30g => DISLIKE
      final monB5g = evaluateMealPreference(
        food: 'FOOD_B',
        startingGrams: 35.0,
        remainingGrams: 30.0,
      );
      expect(monB5g.consumedGrams, 5.0);
      expect(monB5g.preference, 'DISLIKE');
      expect(monB5g.conclusion, 'Mèo không thích ăn Món B (DISLIKE)');

      // Món B: Cấp 35g, không ăn (0g, còn 35g) => DISLIKE
      final monB0g = evaluateMealPreference(
        food: 'FOOD_B',
        startingGrams: 35.0,
        remainingGrams: 35.0,
      );
      expect(monB0g.consumedGrams, 0.0);
      expect(monB0g.preference, 'DISLIKE');
      expect(monB0g.conclusion, 'Mèo không thích ăn Món B (DISLIKE)');
    },
  );

  testWidgets(
    'Flutter Web displays Mon A LIKE and Mon B DISLIKE logs on History and Feeding tabs',
    (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);

      final backend = MockFeederBackend();
      addTearDown(backend.dispose);
      await tester.pumpWidget(FeederDemoApp(backend: backend));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Lịch sử'));
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('Phân tích Hành vi Ăn uống & Sở thích (Món A / Món B)'),
        250,
      );
      expect(
        find.text('Phân tích Hành vi Ăn uống & Sở thích (Món A / Món B)'),
        findsOneWidget,
      );
      expect(find.text('Mèo thích ăn Món A (LIKE)'), findsWidgets);
      expect(find.text('Mèo không thích ăn Món B (DISLIKE)'), findsWidgets);
      expect(
        find.textContaining('Cấp: 35 g · Đã ăn: 33.0 g (94.3%) · Còn lại: 2.0 g'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Cấp: 35 g · Đã ăn: 3.0 g (8.6%) · Còn lại: 32.0 g'),
        findsOneWidget,
      );
    },
  );
}
