import 'feeder_backend.dart';
import 'mock_backend.dart';
import 'real_backend.dart';

FeederBackend createBackend() {
  const mode = String.fromEnvironment('FEEDER_MODE', defaultValue: 'real');
  if (mode == 'mock') return MockFeederBackend();
  if (mode != 'real') throw StateError('FEEDER_MODE must be real or mock');
  const configured = String.fromEnvironment('FEEDER_API_BASE_URL');
  final base = configured.isEmpty ? Uri.base : Uri.parse(configured);
  final subSource = Uri.base.path.contains('kiosk') ? 'KIOSK' : 'APP';
  return RealFeederBackend(base: base, subSource: subSource);
}
