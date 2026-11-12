import 'dart:convert';

import 'package:feeder_demo/live_camera_controller.dart';
import 'package:feeder_demo/live_camera_panel.dart';
import 'package:feeder_demo/mock_backend.dart';
import 'package:feeder_demo/user_pages.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

Map<String, dynamic> status({
  String state = 'CAMERA_ONLINE',
  bool simulated = true,
}) => {
  'status': state,
  'source': simulated ? 'SIMULATED' : 'REAL',
  'simulated': simulated,
  'actuator_execution': false,
  'width': 640,
  'height': 480,
  'frame_age_seconds': .1,
  'annotations': 'BURNED_IN_SAME_FRAME_NOT_STATUS_OVERLAY',
  'stream_lease_seconds': 300,
};
void main() {
  testWidgets('overview backend notifications preserve active camera state', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final backend = MockFeederBackend();
    addTearDown(backend.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AnimatedBuilder(
            animation: backend,
            builder: (context, _) =>
                OverviewPage(backend: backend, onFeed: () {}, onHistory: () {}),
          ),
        ),
      ),
    );
    await tester.scrollUntilVisible(find.text('Xem camera'), 200);
    await tester.ensureVisible(find.text('Xem camera'));
    await tester.pump();
    await tester.tap(find.text('Xem camera'));
    await tester.pump(const Duration(milliseconds: 250));
    expect(find.text('LIVE · SIMULATED'), findsOneWidget);
    backend.connectionError = 'Transient connection update';
    backend.notifyListeners();
    await tester.pump();
    expect(find.text('LIVE · SIMULATED'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(), isNull);
  });
  test(
    'same-origin status + first decoded image required for LIVE; reconnect',
    () async {
      var current = status();
      final c = LiveCameraController(
        base: Uri.parse('https://for-cat.example.ts.net/app'),
        origin: Uri.parse('https://for-cat.example.ts.net/flutter/'),
        client: MockClient((r) async {
          expect(r.url.path, '/api/v1/camera/status');
          return http.Response(jsonEncode(current), 200);
        }),
      );
      addTearDown(c.dispose);
      await c.start();
      expect(c.phase, CameraPhase.connecting);
      expect(c.simulated, isTrue);
      c.firstFrame();
      expect(c.phase, CameraPhase.live);
      final initial = c.generation;
      current = status(state: 'CAMERA_OFFLINE');
      await c.refresh();
      expect(c.phase, CameraPhase.offline);
      current = status(simulated: false);
      await c.refresh();
      expect(c.generation, greaterThan(initial));
      expect(c.phase, CameraPhase.connecting);
      expect(c.simulated, isFalse);
      c.stop();
      expect(c.phase, CameraPhase.off);
      expect(c.wanted, isFalse);
    },
  );
  test(
    'cross-origin Pages cannot fetch private camera or embed secret URL',
    () async {
      var requests = 0;
      final c = LiveCameraController(
        base: Uri.parse('https://for-cat.example.ts.net'),
        origin: Uri.parse('https://demo.pages.dev'),
        client: MockClient((_) async {
          requests++;
          return http.Response('{}', 200);
        }),
      );
      addTearDown(c.dispose);
      await c.start();
      expect(c.phase, CameraPhase.error);
      expect(requests, 0);
      expect(c.error, contains('cùng origin'));
      expect(c.streamUri.queryParameters.keys, isNot(contains('token')));
    },
  );
  test('bad metadata/source and permissions never become LIVE', () async {
    var response = http.Response(jsonEncode({...status(), 'width': 0}), 200);
    final c = LiveCameraController(
      base: Uri.parse('http://localhost:8000'),
      origin: Uri.parse('http://localhost:8000/app'),
      client: MockClient((_) async => response),
    );
    addTearDown(c.dispose);
    await c.start();
    expect(c.phase, CameraPhase.error);
    response = http.Response(
      jsonEncode({...status(), 'simulated': false}),
      200,
    );
    await c.refresh();
    expect(c.phase, CameraPhase.error);
    response = http.Response('denied', 403);
    await c.refresh();
    expect(c.error, contains('VIEW_CAMERA'));
    expect(c.phase, CameraPhase.error);
  });
  testWidgets('MOCK camera opt-in is visibly SIMULATED; off cancels updates', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: LiveCameraPanel(
              isMock: true,
              mockClassification: 'DOG',
              mockRoiEnabled: true,
            ),
          ),
        ),
      ),
    );
    expect(find.text('Xem camera'), findsOneWidget);
    expect(find.text('OFF · SIMULATED'), findsOneWidget);
    await tester.tap(find.text('Xem camera'));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('LIVE · SIMULATED'), findsOneWidget);
    expect(find.byType(CustomPaint), findsWidgets);
    await tester.tap(find.text('Tắt camera'));
    await tester.pump();
    expect(find.text('OFF · SIMULATED'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'REAL panel removes stream when offline and restarts with new generation',
    (tester) async {
      var current = status();
      VoidCallback? decoded;
      final c = LiveCameraController(
        base: Uri.parse('http://localhost:8000'),
        origin: Uri.parse('http://localhost:8000'),
        client: MockClient(
          (_) async => http.Response(jsonEncode(current), 200),
        ),
      );
      addTearDown(c.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: LiveCameraPanel(
                isMock: false,
                controller: c,
                imageBuilder: (uri, onFrame, onError) {
                  decoded = onFrame;
                  return const SizedBox(key: ValueKey('fake-mjpeg'));
                },
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Xem camera'));
      await tester.pump();
      await tester.pump();
      expect(find.byKey(const ValueKey('fake-mjpeg')), findsOneWidget);
      expect(c.phase, CameraPhase.connecting);
      decoded!();
      await tester.pump();
      expect(find.text('LIVE · SIMULATED'), findsOneWidget);
      current = status(state: 'CAMERA_OFFLINE');
      await c.refresh();
      await tester.pump();
      expect(find.byKey(const ValueKey('fake-mjpeg')), findsNothing);
      expect(find.textContaining('CAMERA_OFFLINE'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
