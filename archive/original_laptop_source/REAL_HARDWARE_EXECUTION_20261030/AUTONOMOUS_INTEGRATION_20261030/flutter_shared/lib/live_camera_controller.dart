import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

enum CameraPhase { off, connecting, live, offline, error }

class LiveCameraController extends ChangeNotifier {
  final Uri base, origin;
  final http.Client client;
  final Duration pollInterval;
  Timer? _timer;
  bool wanted = false, simulated = false, decoded = false;
  bool _disposed = false;
  int _intent = 0;
  int? _pollIntent;
  String? _producerEpoch;
  String? _source;
  CameraPhase phase = CameraPhase.off;
  String? error;
  int width = 640, height = 480, generation = 0;
  DateTime? _opened;
  Duration _renewAfter = const Duration(minutes: 4);

  LiveCameraController({
    required this.base,
    Uri? origin,
    http.Client? client,
    this.pollInterval = const Duration(seconds: 1),
  }) : origin = origin ?? Uri.base,
       client = client ?? http.Client();

  Uri get streamUri => base
      .resolve('/api/v1/camera/mjpeg')
      .replace(queryParameters: {'view': '$generation'});

  bool get sameOrigin =>
      ['http', 'https'].contains(base.scheme) &&
      ['http', 'https'].contains(origin.scheme) &&
      base.origin == origin.origin &&
      (base.scheme == 'https' ||
          ['localhost', '127.0.0.1', '::1'].contains(base.host)) &&
      base.userInfo.isEmpty;

  Future<void> start() async {
    if (_disposed || wanted) return;
    wanted = true;
    final intent = ++_intent;
    decoded = false;
    error = null;
    if (!sameOrigin) {
      phase = CameraPhase.error;
      error = 'Camera cần cùng origin HTTPS. Hãy mở trang riêng trên Jetson qua Tailscale Serve.';
      notifyListeners();
      return;
    }
    phase = CameraPhase.connecting;
    notifyListeners();
    await refresh();
    if (!_disposed && wanted && intent == _intent) {
      _timer = Timer.periodic(pollInterval, (_) => unawaited(refresh()));
    }
  }

  Future<void> refresh() async {
    if (_disposed || !wanted || _pollIntent == _intent || !sameOrigin) return;
    final intent = _intent;
    _pollIntent = intent;
    try {
      final response = await client
          .get(base.resolve('/api/v1/camera/status?watch=true'))
          .timeout(const Duration(seconds: 3));
      if (_disposed || !wanted || intent != _intent) return;
      if (response.statusCode == 403 || response.statusCode == 401) {
        phase = CameraPhase.error;
        error = 'Không có quyền VIEW_CAMERA hoặc camera chưa được cấu hình an toàn.';
        decoded = false;
        notifyListeners();
        return;
      }
      if (response.statusCode != 200) {
        throw const FormatException('Camera status unavailable');
      }
      final value = jsonDecode(response.body);
      if (value is! Map<String, dynamic> ||
          !['REAL', 'SIMULATED'].contains(value['source']) ||
          value['simulated'] != (value['source'] == 'SIMULATED') ||
          value['actuator_execution'] != false) {
        throw const FormatException('Invalid camera source contract');
      }
      final sourceChanged = _source != null && _source != value['source'];
      final epoch = value['producer_epoch'];
      if (epoch != null && (epoch is! String || epoch.isEmpty)) {
        throw const FormatException('Invalid producer identity');
      }
      final epochChanged = _producerEpoch != null && _producerEpoch != epoch;
      _source = value['source'] as String;
      simulated = value['simulated'] as bool;
      if (value['status'] == 'CAMERA_OFFLINE') {
        phase = CameraPhase.offline;
        decoded = false;
        error = null;
      } else if (value['status'] == 'CAMERA_ONLINE') {
        final w = value['width'],
            h = value['height'],
            age = value['frame_age_seconds'];
        if (w is! int ||
            h is! int ||
            w < 2 ||
            h < 2 ||
            w > 1280 ||
            h > 960 ||
            age is! num ||
            !age.isFinite ||
            age < 0 ||
            age > 2 ||
            value['annotations'] != 'BURNED_IN_SAME_FRAME_NOT_STATUS_OVERLAY') {
          throw const FormatException('Stale/invalid frame metadata');
        }
        width = w;
        height = h;
        final lease = value['stream_lease_seconds'];
        if (lease is num && lease.isFinite && lease >= 10 && lease <= 600) {
          _renewAfter = Duration(seconds: (lease - 5).floor().clamp(5, 240));
        }
        final reconnect =
            sourceChanged || epochChanged ||
            phase == CameraPhase.offline ||
            phase == CameraPhase.error ||
            _opened == null ||
            DateTime.now().difference(_opened!) > _renewAfter;
        if (reconnect) {
          generation++;
          decoded = false;
          _opened = DateTime.now();
        }
        _producerEpoch = epoch as String?;
        phase = decoded ? CameraPhase.live : CameraPhase.connecting;
        error = null;
      } else {
        throw const FormatException('Unknown camera state');
      }
    } catch (_) {
      if (!_disposed && wanted && intent == _intent) {
        phase = CameraPhase.error;
        decoded = false;
        error = 'Không kết nối được camera; chưa có hình trực tiếp.';
      }
    } finally {
      if (_pollIntent == intent) _pollIntent = null;
      if (!_disposed && wanted && intent == _intent) notifyListeners();
    }
  }

  void firstFrame([int? imageGeneration]) {
    if (imageGeneration != null && imageGeneration != generation) return;
    if (!_disposed && wanted && phase == CameraPhase.connecting) {
      decoded = true;
      phase = CameraPhase.live;
      notifyListeners();
    }
  }

  void streamError([int? imageGeneration]) {
    if (imageGeneration != null && imageGeneration != generation) return;
    if (!_disposed && wanted) {
      decoded = false;
      phase = CameraPhase.error;
      error =
          'Stream bị ngắt hoặc bị từ chối. Đang kiểm tra lại kết nối/quyền.';
      notifyListeners();
    }
  }

  void stop() {
    ++_intent;
    wanted = false;
    decoded = false;
    _timer?.cancel();
    _timer = null;
    phase = CameraPhase.off;
    _opened = null;
    _producerEpoch = null;
    _source = null;
    generation++;
    notifyListeners();
  }

  @override
  void dispose() {
    ++_intent;
    _disposed = true;
    _timer?.cancel();
    client.close();
    super.dispose();
  }
}
