import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'feeder_backend.dart';
import 'feeder_state.dart';
import 'pending_store.dart';
import 'meal_plans.dart';
import 'history_model.dart';
import 'status_model.dart';

abstract class StateSocket {
  Stream<dynamic> get stream;
  Future<void> get ready;
  Future<void> close();
}

class ChannelSocket implements StateSocket {
  final WebSocketChannel channel;
  ChannelSocket(Uri uri) : channel = WebSocketChannel.connect(uri);
  @override
  Stream<dynamic> get stream => channel.stream;
  @override
  Future<void> get ready => channel.ready;
  @override
  Future<void> close() async {
    await channel.sink.close();
  }
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
  bool _disposed = false,
      _started = false,
      _historyBusy = false,
      _storageError = false;
  String? _pendingId;
  String? _visualSignature;
  int parseErrors = 0, reconnects = 0;
  @override
  String get endpoint => base.toString();
  String? get pendingId => _pendingId;
  @override
  bool get isMock => false;
  @override
  bool get canFeed => super.canFeed && !_storageError;

  RealFeederBackend({
    required this.base,
    required this.subSource,
    http.Client? client,
    PendingStore? store,
    StateSocket Function(Uri)? socketFactory,
    String Function()? idFactory,
    this.staleAfter = const Duration(seconds: 3),
    this.requestWindow = const Duration(seconds: 20),
    this.pollInterval = const Duration(milliseconds: 250),
  }) : client = client ?? http.Client(),
       store = store ?? createPendingStore(subSource),
       socketFactory = socketFactory ?? ChannelSocket.new,
       idFactory =
           idFactory ??
           (() {
             final r = Random.secure();
             return List.generate(
               16,
               (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0'),
             ).join();
           }) {
    mealPreferenceLogs.clear(); // REAL never starts with demo meal results.
    if (!['KIOSK', 'APP'].contains(subSource)) {
      throw ArgumentError('Invalid manual sub-source');
    }
    try {
      final saved = this.store.load();
      if (saved != null) {
        final value = object(jsonDecode(saved));
        final id = value['request_id'];
        if (id is! String ||
            !RegExp(r'^[A-Za-z0-9_-]{1,64}$').hasMatch(id) ||
            value['sub_source'] != subSource ||
            value['target_grams'] != 35) {
          throw const FormatException('Invalid saved request');
        }
        _pendingId = id;
      }
    } catch (_) {
      _storageError = true;
      requestError = 'Không đọc được ID đã lưu; chưa gửi request mới.';
    }
  }
  Uri uri(String path) => base.resolve(path);
  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _invalidate(String error, {bool stale = false, bool malformed = false}) {
    scheduledWorker = ScheduledWorkerStatus.unknown();
    scheduledOccurrences.clear();
    _visualSignature = null;
    state = FeederState.unknown(health: 'UNKNOWN');
    connectionStatus = stale
        ? AppStatus.stale
        : malformed
        ? AppStatus.unknown
        : AppStatus.offline;
    connectionError = error;
    _notify();
  }

  void _accept(String body) {
    final next = FeederState.decode(body);
    final visual = Map<String, dynamic>.from(next.data)..remove('observed_at');
    final signature = jsonEncode(visual);
    final changed = signature != _visualSignature || connectionError != null;
    final previousMeal = state.data['meal_id'];
    final previousPhase = state.data['meal_phase'];
    state = next;
    final chosen = next.data['selected_food'];
    if (chosen == 'FOOD_A' || chosen == 'FOOD_B') {
      selectedFood = chosen as String;
    }
    if (next.data['meal_phase'] == 'FINAL' &&
        (previousMeal != next.data['meal_id'] || previousPhase != 'FINAL')) {
      unawaited(refreshMealObservation());
    }
    connectionStatus = AppStatus.online;
    _lastState = _clock.elapsed;
    connectionError = null;
    _retry = 0;
    _visualSignature = signature;
    if (changed) _notify();
  }

  @override
  Future<void> start() async {
    if (_started || _disposed) return;
    _started = true;
    if (!['http', 'https'].contains(base.scheme) || base.host.isEmpty) {
      _invalidate('API chưa cấu hình');
      return;
    }
    _watchdog = Timer.periodic(const Duration(milliseconds: 250), (_) {
      if (_lastState != null && _clock.elapsed - _lastState! > staleAfter) {
        _lost(_generation, stale: true);
      }
    });
    _history = Timer.periodic(const Duration(seconds: 10), (_) {
      unawaited(refreshHistory());
      unawaited(refreshMealPlans());
      unawaited(refreshCalibration());
      unawaited(refreshMealObservation());
    });
    unawaited(refreshHistory());
    unawaited(refreshMealPlans());
    unawaited(refreshCalibration());
    unawaited(refreshMealObservation());
    unawaited(_connect());
    if (_pendingId != null) {
      unawaited(_request(post: false)); // restore is GET only
    }
  }

  Future<void> _connect() async {
    if (_disposed) return;
    final generation = ++_generation;
    try {
      final response = await client
          .get(uri('/api/status'))
          .timeout(const Duration(seconds: 3));
      if (_disposed || generation != _generation) return;
      if (response.statusCode != 200) {
        throw StateError('HTTP ${response.statusCode}');
      }
      _accept(response.body);
    } catch (_) {
      if (!_disposed && generation == _generation) {
        _invalidate('Không đọc được REST state');
      }
    }
    if (_disposed || generation != _generation) return;
    try {
      final address = uri('/api/ws/state')
          .replace(scheme: base.scheme == 'https' ? 'wss' : 'ws');
      final socket = socketFactory(address);
      _socket = socket;
      _subscription = socket.stream.listen(
        (dynamic message) {
          if (_disposed || generation != _generation) return;
          try {
            if (message is! String) {
              throw const FormatException('Non-text state');
            }
            _accept(message);
          } catch (_) {
            parseErrors++;
            _invalidate(
              'BAD_TELEMETRY — dữ liệu không hợp lệ',
              malformed: true,
            );
          }
        },
        onError: (Object error) => _lost(generation),
        onDone: () => _lost(generation),
        cancelOnError: true,
      );
      await socket.ready.timeout(const Duration(seconds: 3));
    } catch (_) {
      _lost(generation);
    }
  }

  void _lost(int generation, {bool stale = false}) {
    if (_disposed || generation != _generation) return;
    ++_generation;
    _lastState = null;
    _invalidate(
      stale ? 'Realtime STALE — ẩn số cũ' : 'Realtime DISCONNECTED — ẩn số cũ',
      stale: stale,
    );
    unawaited(_subscription?.cancel() ?? Future<void>.value());
    _subscription = null;
    unawaited(
      _socket?.close().catchError((Object _) {}) ?? Future<void>.value(),
    );
    _socket = null;
    _reconnect?.cancel();
    final wait = min(5000, 250 * (1 << min(_retry++, 4)));
    _reconnect = Timer(Duration(milliseconds: wait), () {
      reconnects++;
      unawaited(_connect());
    });
  }

  Future<http.Response> _jsonGet(String path) =>
      client.get(uri(path)).timeout(const Duration(seconds: 5));
  Future<void> _request({required bool post}) async {
    if (feeding || _pendingId == null || _disposed) return;
    feeding = true;
    requestError = null;
    receipt = null;
    _notify();
    final id = _pendingId!;
    try {
      final payload = {
        'request_id': id,
        'sub_source': subSource,
        'target_grams': 35,
      };
      var response = post
          ? await client
                .post(
                  uri('/api/feed/preview'),
                  headers: {'Content-Type': 'application/json'},
                  body: jsonEncode(payload),
                )
                .timeout(const Duration(seconds: 5))
          : await _jsonGet('/api/feed/preview/$id');
      final deadline = _clock.elapsed + requestWindow;
      while (!_disposed) {
        if (response.statusCode != 200 && response.statusCode != 202) {
          throw StateError(
            'HTTP ${response.statusCode}: chưa xác nhận kết quả',
          );
        }
        receipt = PreviewReceipt.decode(response.body, id, subSource);
        _notify();
        if (receipt!.complete) {
          try {
            store.clear();
          } catch (_) {
            /* old ID is safe to query again after reload */
          }
          _pendingId = null;
          final entry = HistoryEntry.fromReceipt(receipt!);
          if (entry != null) _receiptHistory[entry.id] = entry;
          while (_receiptHistory.length > 50) {
            _receiptHistory.remove(_receiptHistory.keys.first);
          }
          _rebuildHistory();
          unawaited(refreshHistory());
          break;
        }
        if (_clock.elapsed >= deadline) {
          throw TimeoutException('Arbiter chưa trả decision');
        }
        await Future<void>.delayed(pollInterval);
        if (_disposed) return;
        response = await _jsonGet('/api/feed/preview/$id');
      }
    } catch (_) {
      if (!_disposed) {
        requestError = 'Chưa xác nhận kết quả. Thử lại dùng cùng ID: $id';
      }
    } finally {
      feeding = false;
      _notify();
    }
  }

  @override
  Future<void> feed() async {
    if (!canFeed || _disposed) return;
    if (_pendingId == null &&
        _lastIntent != null &&
        _clock.elapsed - _lastIntent! < const Duration(seconds: 1)) {
      return;
    }
    try {
      _pendingId ??= 'flutter_${subSource.toLowerCase()}_${idFactory()}';
      if (!RegExp(r'^[A-Za-z0-9_-]{1,64}$').hasMatch(_pendingId!)) {
        throw const FormatException('Invalid request ID');
      }
      store.save(
        jsonEncode({
          'request_id': _pendingId,
          'sub_source': subSource,
          'target_grams': 35,
        }),
      );
      _lastIntent = _clock.elapsed;
    } catch (_) {
      _storageError = true;
      requestError = 'Không lưu được request ID; chưa gửi request.';
      _notify();
      return;
    }
    await _request(post: true);
  }

  @override
  Future<void> refreshHistory() async {
    if (_disposed || _historyBusy || !['http', 'https'].contains(base.scheme)) {
      return;
    }
    _historyBusy = true;
    try {
      final response = await _jsonGet('/api/v1/esp32/events?limit=100');
      if (_disposed) return;
      if (response.statusCode != 200 || response.body.length > 1024 * 1024) {
        throw StateError('History unavailable');
      }
      final events = jsonDecode(response.body);
      if (events is! List || events.length > 100) {
        throw const FormatException('Invalid history');
      }
      _eventHistory = events
          .map(HistoryEntry.fromEvent)
          .whereType<HistoryEntry>()
          .toList();
      historyLoaded = true;
      historyError = null;
      _rebuildHistory();
    } catch (_) {
      if (!_disposed) {
        historyError =
            'Lịch sử có thể chưa cập nhật; chưa đọc được event từ Jetson.';
      }
    } finally {
      _historyBusy = false;
      _notify();
    }
  }

  List<HistoryEntry> _eventHistory = [], _occurrenceHistory = [];
  final Map<String, HistoryEntry> _receiptHistory = {};
  void _rebuildHistory() {
    historyRecords
      ..clear()
      ..addAll(
        mergeHistory(_eventHistory, _occurrenceHistory, _receiptHistory.values),
      );
    activity
      ..clear()
      ..addAll(historyRecords.map((e) => e.legacyText));
    _notify();
  }

  bool _observationRefreshing = false;
  @override
  Future<void> refreshMealObservation() async {
    if (_disposed || _observationRefreshing) return;
    _observationRefreshing = true;
    try {
      final response = await _jsonGet('/api/meal-observation');
      if (_disposed) return;
      if (response.statusCode != 200) {
        throw StateError('Meal observations unavailable');
      }
      final body = object(jsonDecode(response.body));
      final records = body['records'];
      if (records is! List || records.length > 20) {
        throw const FormatException('Invalid meal records');
      }
      final parsed = <MealPreferenceResult>[];
      final seen = <String>{};
      for (final raw in records) {
        final m = object(raw), food = text(object(raw)['food']);
        final start = number(m['starting_g']),
            remaining = number(m['remaining_g']);
        final id = text(m['meal_id']);
        final at = DateTime.tryParse(text(m['timestamp']));
        if (m['schema_version'] != 2 ||
            m['final'] != true ||
            id.isEmpty ||
            !seen.add(id) ||
            !['FOOD_A', 'FOOD_B'].contains(food) ||
            start == null ||
            remaining == null ||
            start <= 0 ||
            remaining < 0 ||
            remaining > start ||
            at == null) {
          continue;
        }
        parsed.add(
          evaluateMealPreference(
            food: food,
            startingGrams: start,
            remainingGrams: remaining,
            timestamp: at,
            id: id,
            isManualTest: m['observation_mode'] == 'MANUAL_TEST',
          ),
        );
      }
      mealPreferenceLogs
        ..clear()
        ..addAll(parsed);
      mealObservationSupported = true;
      mealObservationError = null;
    } catch (_) {
      if (!_disposed) {
        mealObservationError = 'Chưa cập nhật được kết quả bữa ăn.';
      }
    } finally {
      _observationRefreshing = false;
      _notify();
    }
  }

  Future<void> _mealAction(String action) async {
    if (_disposed || mealObservationBusy) return;
    mealObservationBusy = true;
    mealObservationError = null;
    _notify();
    try {
      final response = await client
          .post(
            uri('/api/meal-observation'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'action': action}),
          )
          .timeout(const Duration(seconds: 3));
      if (_disposed) return;
      final body = object(jsonDecode(response.body));
      if (response.statusCode != 202 || body['queued'] != true) {
        mealObservationError = text(
          body['detail'],
          'Chưa thực hiện được thao tác.',
        );
      }
    } catch (_) {
      if (!_disposed) {
        mealObservationError =
            'Chưa xác nhận thao tác; hãy kiểm tra trạng thái máy.';
      }
    } finally {
      mealObservationBusy = false;
      _notify();
    }
  }

  @override
  Future<void> setMealFood(String code) =>
      _mealAction(code == 'FOOD_B' ? 'SELECT_B' : 'SELECT_A');
  @override
  Future<void> finishMealObservation() => _mealAction('FINISH');

  bool _calibrationBusy = false;
  @override
  Future<void> refreshCalibration() async {
    if (_disposed ||
        _calibrationBusy ||
        !['http', 'https'].contains(base.scheme)) {
      return;
    }
    _calibrationBusy = true;
    try {
      final response = await _jsonGet('/api/hx711/calibration');
      if (_disposed) return;
      if (response.statusCode == 404) {
        calibrationInfo = null;
        calibrationSupported = false;
        calibrationError = null;
        return;
      }
      if (response.statusCode != 200 || response.body.length > 131072) {
        throw StateError('Calibration metadata unavailable');
      }
      final body = object(jsonDecode(response.body));
      if (body['error'] != null ||
          body['actuator_execution'] != false ||
          body['actual_dispensed_grams'] != null) {
        throw const FormatException('Invalid calibration metadata');
      }
      calibrationInfo = body;
      calibrationSupported = true;
      calibrationError = null;
    } catch (_) {
      if (!_disposed) {
        calibrationInfo = null;
        calibrationSupported = null;
        calibrationError = 'Chưa đọc được metadata hiệu chuẩn.';
      }
    } finally {
      _calibrationBusy = false;
      _notify();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    ++_generation;
    _watchdog?.cancel();
    _reconnect?.cancel();
    _history?.cancel();
    unawaited(_subscription?.cancel() ?? Future<void>.value());
    unawaited(
      _socket?.close().catchError((Object _) {}) ?? Future<void>.value(),
    );
    client.close();
    super.dispose();
  }

  bool _planRefreshBusy = false;
  int _planGeneration = 0;
  String? _pendingPlanCreateId;
  Future<void> _loadPlans() async {
    final generation = _planGeneration;
    final response = await _jsonGet('/api/meal-plans');
    if (_disposed || generation != _planGeneration) return;
    if (response.statusCode != 200 || response.body.length > 65536) {
      throw StateError('Meal Plan unavailable');
    }
    final value = object(jsonDecode(response.body));
    final raw = value['plans'];
    if (raw is! List ||
        raw.length > 32 ||
        !scheduleMode(value['mode']) ||
        value['autonomous_worker_enabled'] is! bool ||
        value['actuator_execution'] != false) {
      throw const FormatException('Invalid Meal Plan list');
    }
    final parsed = raw.map(MealPlan.decode).toList();
    final worker = value['worker'] == null
        ? ScheduledWorkerStatus.unknown()
        : ScheduledWorkerStatus.decode(value['worker']);
    if (value['autonomous_worker_enabled'] == true && worker.enabled != true) {
      throw const FormatException('Missing autonomous worker state');
    }
    if (worker.enabled != null &&
        worker.enabled != value['autonomous_worker_enabled']) {
      throw const FormatException('Conflicting worker state');
    }
    final occurrences = decodeOccurrences(value['recent_occurrences']);
    if (parsed.map((p) => p.id).toSet().length != parsed.length) {
      throw const FormatException('Duplicate plans');
    }
    mealPlans
      ..clear()
      ..addAll(parsed);
    scheduledWorker = worker;
    scheduledOccurrences
      ..clear()
      ..addAll(occurrences);
    plansLoaded = true;
    _occurrenceHistory = occurrences
        .map(HistoryEntry.fromOccurrence)
        .whereType<HistoryEntry>()
        .toList();
    historyLoaded = true;
    _rebuildHistory();
    if (parsed.any((plan) => plan.id == _pendingPlanCreateId)) {
      _pendingPlanCreateId = null;
    }
    plansError = value['errors'] is List && (value['errors'] as List).isNotEmpty
        ? 'Có cấu hình lỗi đã được cách ly; tải lại để kiểm tra.'
        : null;
  }

  @override
  Future<void> refreshMealPlans() async {
    if (_disposed ||
        plansBusy ||
        _planRefreshBusy ||
        !['http', 'https'].contains(base.scheme)) {
      return;
    }
    _planRefreshBusy = true;
    try {
      await _loadPlans();
    } catch (_) {
      if (!_disposed) {
        scheduledWorker = ScheduledWorkerStatus.unknown();
        scheduledOccurrences.clear();
        plansError = 'Chưa tải được Meal Plan từ Jetson. Không dùng lịch mẫu.';
      }
    } finally {
      _planRefreshBusy = false;
      _notify();
    }
  }

  Future<http.Response> _planWrite(
    String method,
    String path,
    Map<String, dynamic> body,
  ) {
    final headers = {'Content-Type': 'application/json'};
    if (method == 'PUT') {
      return client
          .put(uri(path), headers: headers, body: jsonEncode(body))
          .timeout(const Duration(seconds: 5));
    }
    if (method == 'DELETE') {
      return client
          .delete(uri(path), headers: headers, body: jsonEncode(body))
          .timeout(const Duration(seconds: 5));
    }
    return client
        .post(uri(path), headers: headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 5));
  }

  Future<void> _planAction(Future<void> Function() action) async {
    if (_disposed || plansBusy) return;
    plansBusy = true;
    plansError = null;
    ++_planGeneration;
    _notify();
    try {
      await action();
    } catch (_) {
      if (!_disposed) {
        plansError =
            'Chưa xác nhận thao tác lịch. Tải lại từ Jetson trước khi thử lại.';
      }
    } finally {
      plansBusy = false;
      _notify();
    }
  }

  @override
  Future<void> saveMealPlan({
    MealPlan? existing,
    required String name,
    required String localTime,
    required List<int> weekdays,
    required bool enabled,
  }) => _planAction(() async {
    final id = existing?.id ?? (_pendingPlanCreateId ??= 'plan_${idFactory()}');
    final payload = {
      'name': name.trim(),
      'local_time': localTime,
      'weekdays': weekdays,
      'enabled': enabled,
      'target_grams': 35,
      'timezone': 'Asia/Ho_Chi_Minh',
      if (existing == null)
        'plan_id': id
      else
        'expected_revision': existing.revision,
    };
    final response = await _planWrite(
      existing == null ? 'POST' : 'PUT',
      existing == null ? '/api/meal-plans' : '/api/meal-plans/$id',
      payload,
    );
    if (_disposed) return;
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw StateError('Plan save HTTP ${response.statusCode}');
    }
    final saved = MealPlan.decode(jsonDecode(response.body));
    if (saved.id != id) throw const FormatException('Unexpected plan ID');
    if (existing == null) _pendingPlanCreateId = null;
    await _loadPlans();
  });
  @override
  Future<void> deleteMealPlan(MealPlan plan) => _planAction(() async {
    final response = await _planWrite('DELETE', '/api/meal-plans/${plan.id}', {
      'expected_revision': plan.revision,
    });
    if (_disposed) return;
    final body = object(jsonDecode(response.body));
    if (response.statusCode != 200 ||
        body['deleted'] != true ||
        body['plan_id'] != plan.id ||
        body['actuator_execution'] != false) {
      throw StateError('Plan delete unconfirmed');
    }
    await _loadPlans();
  });
  @override
  Future<void> previewMealPlan(MealPlan plan) => _planAction(() async {
    schedulePreview = null;
    scheduledReceipt = null;
    final response = await _planWrite(
      'POST',
      '/api/meal-plans/${plan.id}/preview',
      {'expected_revision': plan.revision},
    );
    if (_disposed) return;
    if (response.statusCode != 200) {
      throw StateError('Schedule preview HTTP ${response.statusCode}');
    }
    schedulePreview = SchedulePreview.decode(response.body, plan);
    scheduledReceipt = schedulePreview!.receipt;
    _notify();
    final deadline = _clock.elapsed + requestWindow;
    while (!_disposed &&
        scheduledReceipt != null &&
        !scheduledReceipt!.complete) {
      if (_clock.elapsed >= deadline) {
        throw TimeoutException('Scheduled arbiter decision pending');
      }
      await Future<void>.delayed(pollInterval);
      if (_disposed) return;
      final receiptResponse = await _jsonGet(
        '/api/feed/preview/${scheduledReceipt!.id}',
      );
      if (_disposed) return;
      if (receiptResponse.statusCode != 200 &&
          receiptResponse.statusCode != 202) {
        throw StateError('Scheduled receipt unavailable');
      }
      scheduledReceipt = PreviewReceipt.decode(
        receiptResponse.body,
        scheduledReceipt!.id,
        '',
        source: 'SCHEDULED',
      );
      _notify();
    }
    unawaited(refreshHistory());
  });
}
