import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'pending_store.dart';

abstract class StateSocket {
  Stream<dynamic> get stream;
  Future<void> get ready;
  Future<void> close();
}
class ChannelSocket implements StateSocket {
  final WebSocketChannel channel;
  ChannelSocket(Uri uri) : channel = WebSocketChannel.connect(uri);
  @override Stream<dynamic> get stream => channel.stream;
  @override Future<void> get ready => channel.ready;
  @override Future<void> close() async { await channel.sink.close(); }
}

class RealFeederBackend extends FeederBackend {
  final Uri base;
  final String subSource;
  final http.Client client;
  final PendingStore store;
  final StateSocket Function(Uri) socketFactory;
  final Duration staleAfter, requestWindow, pollInterval;
  final String Function() idFactory;
  final Stopwatch _clock = Stopwatch()..start();
  Timer? _watchdog, _reconnect, _history;
  StreamSubscription<dynamic>? _subscription;
  StateSocket? _socket;
  int _generation = 0, _retry = 0;
  Duration? _lastState, _lastIntent;
  bool _disposed = false, _started = false, _historyBusy = false, _storageError = false;
  String? _pendingId;
  String? _visualSignature;
  int parseErrors = 0, reconnects = 0;
  String get endpoint => base.toString();
  String? get pendingId => _pendingId;
  @override bool get isMock => false;
  @override bool get canFeed => super.canFeed && !_storageError;

  RealFeederBackend({required this.base, required this.subSource, http.Client? client,
    PendingStore? store, StateSocket Function(Uri)? socketFactory, String Function()? idFactory,
    this.staleAfter = const Duration(seconds: 3), this.requestWindow = const Duration(seconds: 20),
    this.pollInterval = const Duration(milliseconds: 250)})
      : client = client ?? http.Client(), store = store ?? createPendingStore(subSource),
        socketFactory = socketFactory ?? ChannelSocket.new,
        idFactory = idFactory ?? (() { final r = Random.secure(); return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0')).join(); }) {
    if (!['KIOSK', 'APP'].contains(subSource)) throw ArgumentError('Invalid manual sub-source');
    try {
      final saved = this.store.load();
      if (saved != null) {
        final value = object(jsonDecode(saved));
        final id = value['request_id'];
        if (id is! String || !RegExp(r'^[A-Za-z0-9_-]{1,64}$').hasMatch(id) ||
            value['sub_source'] != subSource || value['target_grams'] != 35) {
          throw const FormatException('Invalid saved request');
        }
        _pendingId = id;
      }
    } catch (_) { _storageError = true; requestError = 'Không đọc được ID đã lưu; chưa gửi request mới.'; }
  }
  Uri uri(String path) => base.resolve(path);
  void _notify() { if (!_disposed) notifyListeners(); }
  void _invalidate(String error, {bool stale = false}) {
    _visualSignature = null;
    state = FeederState.unknown(health: stale ? 'ESP32_STALE' : 'ESP32_DISCONNECTED');
    connectionError = error; _notify();
  }
  void _accept(String body) {
    final next = FeederState.decode(body);
    final visual = Map<String, dynamic>.from(next.data)..remove('observed_at');
    final signature = jsonEncode(visual);
    final changed = signature != _visualSignature || connectionError != null;
    state = next; _lastState = _clock.elapsed; connectionError = null; _retry = 0;
    _visualSignature = signature;
    if (changed) _notify();
  }
  @override Future<void> start() async {
    if (_started || _disposed) return; _started = true;
    if (!['http', 'https'].contains(base.scheme) || base.host.isEmpty) { _invalidate('API chưa cấu hình'); return; }
    _watchdog = Timer.periodic(const Duration(milliseconds: 250), (_) {
      if (_lastState != null && _clock.elapsed - _lastState! > staleAfter) {
        _lost(_generation, stale: true);
      }
    });
    _history = Timer.periodic(const Duration(seconds: 10), (_) => refreshHistory());
    unawaited(refreshHistory());
    unawaited(_connect());
    if (_pendingId != null) unawaited(_request(post: false)); // restore is GET only
  }
  Future<void> _connect() async {
    if (_disposed) return;
    final generation = ++_generation;
    try {
      final response = await client.get(uri('/api/status')).timeout(const Duration(seconds: 3));
      if (_disposed || generation != _generation) return;
      if (response.statusCode != 200) throw StateError('HTTP ${response.statusCode}');
      _accept(response.body);
    } catch (_) { if (!_disposed && generation == _generation) _invalidate('Không đọc được REST state'); }
    if (_disposed || generation != _generation) return;
    try {
      final address = uri('/api/ws/state').replace(scheme: base.scheme == 'https' ? 'wss' : 'ws');
      final socket = socketFactory(address); _socket = socket;
      _subscription = socket.stream.listen((dynamic message) {
        if (_disposed || generation != _generation) return;
        try {
          if (message is! String) throw const FormatException('Non-text state');
          _accept(message);
        } catch (_) { parseErrors++; _invalidate('BAD_TELEMETRY — dữ liệu không hợp lệ'); }
      }, onError: (Object error) => _lost(generation), onDone: () => _lost(generation), cancelOnError: true);
      await socket.ready.timeout(const Duration(seconds: 3));
    } catch (_) { _lost(generation); }
  }
  void _lost(int generation, {bool stale = false}) {
    if (_disposed || generation != _generation) return;
    ++_generation; _lastState = null; _invalidate(stale ? 'Realtime STALE — ẩn số cũ' : 'Realtime DISCONNECTED — ẩn số cũ', stale: stale);
    unawaited(_subscription?.cancel() ?? Future<void>.value()); _subscription = null;
    unawaited(_socket?.close().catchError((Object _) {}) ?? Future<void>.value()); _socket = null;
    _reconnect?.cancel(); final wait = min(5000, 250 * (1 << min(_retry++, 4)));
    _reconnect = Timer(Duration(milliseconds: wait), () { reconnects++; unawaited(_connect()); });
  }
  Future<http.Response> _jsonGet(String path) => client.get(uri(path)).timeout(const Duration(seconds: 5));
  Future<void> _request({required bool post}) async {
    if (feeding || _pendingId == null || _disposed) return;
    feeding = true; requestError = null; receipt = null; _notify();
    final id = _pendingId!;
    try {
      final payload = {'request_id': id, 'sub_source': subSource, 'target_grams': 35};
      var response = post ? await client.post(uri('/api/feed/preview'), headers: {'Content-Type': 'application/json'},
          body: jsonEncode(payload)).timeout(const Duration(seconds: 5)) : await _jsonGet('/api/feed/preview/$id');
      final deadline = _clock.elapsed + requestWindow;
      while (!_disposed) {
        if (response.statusCode != 200 && response.statusCode != 202) throw StateError('HTTP ${response.statusCode}: chưa xác nhận kết quả');
        receipt = PreviewReceipt.decode(response.body, id, subSource); _notify();
        if (receipt!.complete) {
          try { store.clear(); } catch (_) { /* old ID is safe to query again after reload */ }
          _pendingId = null;
          final summary = 'DRY RUN · $subSource · 35 g · ${receipt!.reason} · chưa cấp thức ăn';
          activity.insert(0, summary); if (activity.length > 50) activity.removeLast();
          unawaited(refreshHistory()); break;
        }
        if (_clock.elapsed >= deadline) throw TimeoutException('Arbiter chưa trả decision');
        await Future<void>.delayed(pollInterval);
        if (_disposed) return;
        response = await _jsonGet('/api/feed/preview/$id');
      }
    } catch (_) { if (!_disposed) requestError = 'Chưa xác nhận kết quả. Thử lại dùng cùng ID: $id'; }
    finally { feeding = false; _notify(); }
  }
  @override Future<void> feed() async {
    if (!canFeed || _disposed) return;
    if (_pendingId == null && _lastIntent != null && _clock.elapsed - _lastIntent! < const Duration(seconds: 1)) return;
    try {
      _pendingId ??= 'flutter_${subSource.toLowerCase()}_${idFactory()}';
      if (!RegExp(r'^[A-Za-z0-9_-]{1,64}$').hasMatch(_pendingId!)) throw const FormatException('Invalid request ID');
      store.save(jsonEncode({'request_id': _pendingId, 'sub_source': subSource, 'target_grams': 35}));
      _lastIntent = _clock.elapsed;
    } catch (_) { _storageError = true; requestError = 'Không lưu được request ID; chưa gửi request.'; _notify(); return; }
    await _request(post: true);
  }
  @override Future<void> refreshHistory() async {
    if (_disposed || _historyBusy || !['http', 'https'].contains(base.scheme)) return;
    _historyBusy = true;
    try {
      final response = await _jsonGet('/api/v1/esp32/events?limit=100');
      if (_disposed || response.statusCode != 200 || response.body.length > 1024 * 1024) return;
      final events = jsonDecode(response.body);
      if (events is! List) return;
      final items = <String>[];
      for (final raw in events) {
        final event = object(raw); final details = object(event['details']);
        if (event['kind'] == 'feed_request_dry_run') {
          items.add('${text(event['timestamp'])} · DRY RUN · ${text(details['sub_source'], text(details['manual_source'], text(details['source'])))} · ${text(details['qualification_reason'])}');
        } else if (event['kind'] == 'system_health_event' || event['kind'] == 'serial_disconnected') {
          items.add('${text(event['timestamp'])} · ${text(details['reason'])}');
        }
        if (items.length >= 30) break;
      }
      activity..clear()..addAll(items); _notify();
    } catch (_) { /* history failure never synthesizes a success event */ }
    finally { _historyBusy = false; }
  }
  @override void dispose() {
    _disposed = true; ++_generation; _watchdog?.cancel(); _reconnect?.cancel(); _history?.cancel();
    unawaited(_subscription?.cancel() ?? Future<void>.value());
    unawaited(_socket?.close().catchError((Object _) {}) ?? Future<void>.value());
    client.close(); super.dispose();
  }
}
