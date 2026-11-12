import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:feeder_demo/reservoir_cards.dart';
import 'package:feeder_demo/feeder_state.dart';

import 'real_backend_test.dart' show backend;
import 'state_fixture.dart';

Map<String, dynamic> data() => {
  ...fixture(),
  'reservoirs': {
    'food': {
      'valid': true,
      'percent': 0,
      'state': 'EMPTY',
      'calibration': 'EMPTY_ONLY',
    },
    'water': {
      'valid': true,
      'percent': 0,
      'state': 'EMPTY',
      'calibration': 'EMPTY_ONLY',
    },
  },
};
void main() {
  testWidgets('both reserves show zero when empty independently of pump Off', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final s = FeederState.decode(jsonEncode(data()));
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              Expanded(
                child: ReservoirCard(state: s, role: 'food'),
              ),
              Expanded(
                child: ReservoirCard(state: s, role: 'water'),
              ),
            ],
          ),
        ),
      ),
    );
    expect(find.text('0%'), findsNWidgets(2));
    expect(find.text('Đã cạn'), findsNWidgets(2));
    expect(find.text('Tạm dừng theo dõi nước'), findsNothing);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'uncalibrated changing level and stale never show invented percent',
    (tester) async {
      final d = jsonDecode(jsonEncode(data())) as Map<String, dynamic>;
      d['reservoirs']['water'] = {
        'valid': true,
        'percent': null,
        'state': 'NEEDS_FULL',
      };
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ReservoirCard(
              state: FeederState.decode(jsonEncode(d)),
              role: 'water',
            ),
          ),
        ),
      );
      expect(find.text('Cần lưu mức đầy'), findsOneWidget);
      expect(find.text('97%'), findsNothing);
      d['esp32']['connected'] = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ReservoirCard(
              state: FeederState.decode(jsonEncode(d)),
              role: 'water',
            ),
          ),
        ),
      );
      expect(find.text('Chưa có dữ liệu'), findsOneWidget);
    },
  );
  test(
    'full capture needs consent, uses calibration route and never water enable',
    () async {
      final posts = <http.Request>[];
      final b = backend(
        MockClient((r) async {
          posts.add(r);
          return http.Response('{"saved":true}', 200);
        }),
      );
      addTearDown(b.dispose);
      expect(await b.saveReservoirFull('food'), isFalse);
      expect(posts, isEmpty);
      expect(await b.saveReservoirFull('food', confirmed: true), isTrue);
      expect(posts.single.url.path, '/api/reservoir-calibration');
      expect(jsonDecode(posts.single.body), {
        'role': 'food',
        'confirmed': true,
      });
    },
  );
}
