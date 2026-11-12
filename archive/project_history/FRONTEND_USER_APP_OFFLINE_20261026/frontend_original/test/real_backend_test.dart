import 'dart:async';
import 'dart:convert';
import 'package:feeder_demo/feeder_state.dart';
import 'package:feeder_demo/pending_store.dart';
import 'package:feeder_demo/real_backend.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'state_fixture.dart';

class FakeSocket implements StateSocket {
  final controller = StreamController<dynamic>.broadcast(sync: true);
  @override Stream<dynamic> get stream => controller.stream;
  @override Future<void> get ready => Future.value();
  @override Future<void> close() => controller.close();
}
Future<void> until(bool Function() condition) async {
  final end = DateTime.now().add(const Duration(seconds: 2));
  while (!condition()) {
    if (DateTime.now().isAfter(end)) fail('bounded fixture wait expired');
    await Future<void>.delayed(const Duration(milliseconds: 10));
  }
}
RealFeederBackend backend(http.Client client, {MemoryPendingStore? store, String sub = 'KIOSK',
    StateSocket Function(Uri)? sockets, Duration? stale, Duration? window}) => RealFeederBackend(
      base: Uri.parse('http://synthetic.invalid'), subSource: sub, client: client, store: store ?? MemoryPendingStore(),
      idFactory: () => 'synthetic_nonce', socketFactory: sockets ?? (_) => FakeSocket(),
      staleAfter: stale ?? const Duration(seconds: 3), requestWindow: window ?? const Duration(seconds: 20),
      pollInterval: const Duration(milliseconds: 1));

void main() {
  test('REAL socket disconnect clears values and reconnect resumes same provider', () async {
    final sockets = <FakeSocket>[];
    final service = backend(MockClient((r) async => http.Response(r.url.path == '/api/status' ? jsonEncode(fixture()) : '[]', 200)),
      sockets: (_) { final s = FakeSocket(); sockets.add(s); return s; });
    addTearDown(service.dispose); await service.start(); await until(() => sockets.isNotEmpty);
    expect(service.state.distance('approach'), 24.8);
    await sockets.first.close(); await until(() => !service.online);
    expect(service.state.rawCounts, isNull); expect(service.state.grams, isNull);
    await until(() => sockets.length == 2);
    sockets.last.controller.add(jsonEncode(fixture(distance: 45.2)));
    await until(() => service.state.distance('approach') == 45.2);
    expect(service.isMock, isFalse);
  });
  test('silent realtime goes STALE; malformed frame clears then recovers', () async {
    final socket = FakeSocket();
    final service = backend(MockClient((r) async => http.Response(r.url.path == '/api/status' ? jsonEncode(fixture()) : '[]', 200)),
      sockets: (_) => socket, stale: const Duration(milliseconds: 50));
    addTearDown(service.dispose); await service.start(); await until(() => service.online);
    socket.controller.add('{broken'); expect(service.online, isFalse); expect(service.parseErrors, 1);
    socket.controller.add(jsonEncode(fixture())); expect(service.online, isTrue);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    expect(service.state.linkHealth, 'ESP32_STALE'); expect(service.state.rawCounts, isNull);
  });
  test('lost reply and retry keep same request ID and one server claim', () async {
    final store = MemoryPendingStore(); final requests = <String>[]; final claims = <String, String>{};
    var lost = true;
    final service = backend(MockClient((r) async {
      if (r.method != 'POST') return http.Response('[]', 200);
      final p = jsonDecode(r.body) as Map<String, dynamic>; final id = p['request_id'] as String; requests.add(id);
      claims.putIfAbsent(id, () => preview(p));
      if (lost) { lost = false; throw http.ClientException('synthetic reply lost after commit'); }
      return http.Response(claims[id]!, 202);
    }), store: store);
    addTearDown(service.dispose); service.state = FeederState.decode(jsonEncode(fixture()));
    await service.feed(); final id = service.pendingId; expect(id, isNotNull); expect(service.requestError, isNotNull);
    await service.feed(); expect(requests, [id, id]); expect(claims.length, 1);
    expect(service.receipt!.reason, 'WEIGHT_NOT_CALIBRATED'); expect(store.value, isNull);
  });
  test('APP request is locked in flight and cannot claim physical success', () async {
    final reply = Completer<http.Response>(); var posts = 0;
    final service = backend(MockClient((r) async {
      if (r.method != 'POST') return http.Response('[]', 200);
      posts++; final p = jsonDecode(r.body) as Map<String, dynamic>;
      expect(p['sub_source'], 'APP'); expect(p['target_grams'], 35);
      return reply.future;
    }), sub: 'APP');
    addTearDown(service.dispose); service.state = FeederState.decode(jsonEncode(fixture()));
    final first = service.feed(); await until(() => posts == 1); await service.feed(); expect(posts, 1);
    reply.complete(http.Response(preview({'request_id': service.pendingId, 'sub_source': 'APP', 'target_grams': 35}), 202));
    await first; expect(service.receipt!.decision['actuator_execution'], isFalse);
    expect(service.receipt!.decision['actual_dispensed_grams'], isNull);
  });
  test('saved pending request resumes GET only; no automatic POST after reload', () async {
    final store = MemoryPendingStore();
    store.save(jsonEncode({'request_id': 'saved_fixture', 'sub_source': 'KIOSK', 'target_grams': 35}));
    final methods = <String>[];
    final service = backend(MockClient((r) async {
      methods.add(r.method);
      if (r.url.path == '/api/status') return http.Response(jsonEncode(fixture()), 200);
      if (r.url.path.contains('/api/feed/preview/')) return http.Response(preview({'request_id': 'saved_fixture', 'sub_source': 'KIOSK', 'target_grams': 35}), 200);
      return http.Response('[]', 200);
    }), store: store);
    addTearDown(service.dispose); await service.start(); await until(() => service.receipt?.complete == true);
    expect(methods.every((m) => m == 'GET'), isTrue); expect(store.value, isNull);
  });
  test('unsafe reply/timeout keep intent, never fabricate a success', () async {
    for (final unsafe in [true, false]) {
      final service = backend(MockClient((r) async {
        if (r.method != 'POST' && !r.url.path.contains('/api/feed/preview/')) return http.Response('[]', 200);
        final p = r.method == 'POST' ? jsonDecode(r.body) as Map<String, dynamic> : {'request_id': 'flutter_kiosk_synthetic_nonce', 'sub_source': 'KIOSK', 'target_grams': 35};
        return http.Response(preview(p, complete: unsafe, unsafe: unsafe), 200);
      }), window: const Duration(milliseconds: 10));
      service.state = FeederState.decode(jsonEncode(fixture())); await service.feed();
      expect(service.pendingId, isNotNull); expect(service.requestError, isNotNull); service.dispose();
    }
  });
}
