import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:for_cat_closed_loop_offline/closed_loop_feed_panel.dart';

Map<String, dynamic> fixture(String name) => Map<String, dynamic>.from(jsonDecode(
    File('${Platform.environment['FORCAT_UI_FIXTURES']}/$name.json').readAsStringSync()) as Map);

void main() {
  testWidgets('actual connected API fixture retains MOCK38g and final proof', (tester) async {
    final entries = decodeHistory(fixture('history'));
    expect(entries.single.source, 'MOCK');
    expect(entries.single.actual, 38);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ClosedLoopHistoryPanel(entries: entries))));
    expect(find.textContaining('MOCK · COMPLETE'), findsOneWidget);
    expect(find.text('Khối lượng thực: 38.00 g'), findsOneWidget);
    expect(find.text('Khối lượng thực: 35.00 g'), findsNothing);
  });
  testWidgets('ACK/PENDING never COMPLETE or valid zero', (tester) async {
    final entries = decodeHistory(fixture('pending'));
    expect(entries.single.actual, isNull);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ClosedLoopHistoryPanel(entries: entries))));
    expect(find.textContaining('PENDING — ACK'), findsOneWidget);
    expect(find.text('Khối lượng thực: Chưa có dữ liệu'), findsOneWidget);
    expect(find.textContaining('0.00 g'), findsNothing);
  });
  testWidgets('overshoot fault keeps last41g without pretending settled measurement', (tester) async {
    final entries = decodeHistory(fixture('fault'));
    expect(entries.single.state, 'FAULT');
    expect(entries.single.actual, isNull);
    expect(entries.single.observed, 41);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ClosedLoopHistoryPanel(entries: entries))));
    expect(find.text('Quan sát cuối: 41.00 g'), findsOneWidget);
  });
  test('mass alone or ACK cannot forge COMPLETE', () {
    final data = fixture('history');
    final row = (data['items'] as List).single as Map<String, dynamic>;
    row['closed'] = false;
    expect(() => decodeHistory(data), throwsFormatException);
    row['closed'] = true;
    row['final_status_received'] = false;
    expect(() => decodeHistory(data), throwsFormatException);
  });
  testWidgets('in-progress servo command is visible without a completion claim', (tester) async {
    final entries = decodeHistory(fixture('progress'));
    expect(entries.single.state, 'PENDING');
    expect(entries.single.servoCommand, 'OPEN_COMMAND');
    expect(entries.single.actual, isNull);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: ClosedLoopHistoryPanel(entries: entries))));
    expect(find.textContaining('GPIO6 · lệnh: OPEN_COMMAND'), findsOneWidget);
    expect(find.textContaining('MOCK · COMPLETE'), findsNothing);
  });
  test('offline REAL promotion is rejected', () {
    final data = fixture('history');
    final row = (data['items'] as List).single as Map<String, dynamic>;
    row['source'] = 'REAL';
    row['capture_verified'] = true;
    row['measurement_source'] = 'ESP32_HX711_CLOSED_LOOP';
    expect(() => decodeHistory(data), throwsFormatException);
  });
  test('real provenance contract needs verified receipt, not a bare label', () {
    final data = fixture('history');
    data['execution_context'] = 'QUALIFIED_DEVICE_RECEIPT';
    final row = (data['items'] as List).single as Map<String, dynamic>;
    row['source'] = 'REAL';
    expect(() => decodeHistory(data), throwsFormatException);
    // Contract fixture only, NOT evidence of real capture/hardware PASS.
    row['capture_verified'] = true;
    row['measurement_source'] = 'ESP32_HX711_CLOSED_LOOP';
    expect(decodeHistory(data).single.source, 'REAL');
  });
  test('missing policy and malformed numeric data rejected', () {
    final data = fixture('history');
    final row = (data['items'] as List).single as Map<String, dynamic>;
    row['actual_dispensed_grams'] = '38';
    expect(() => decodeHistory(data), throwsFormatException);
    row['actual_dispensed_grams'] = 38;
    row['mass_policy'] = {'target_grams': 35, 'tolerance_grams': .2};
    expect(() => decodeHistory(data), throwsFormatException);
  });
  test('GET-only controller clears old data after access/error', () async {
    var code = 200;
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/api/v1/closed-loop/history');
      return http.Response(code == 200 ? jsonEncode(fixture('history')) : '{}', code);
    });
    final controller = ClosedLoopHistoryController(client, Uri.parse('http://localhost:8000/kiosk'));
    await controller.refresh();
    expect(controller.entries.single.actual, 38);
    code = 403;
    await controller.refresh();
    expect(controller.entries, isEmpty);
    expect(controller.sourceStatus, 'NOT_AVAILABLE');
    controller.dispose();client.close();
  });
}
