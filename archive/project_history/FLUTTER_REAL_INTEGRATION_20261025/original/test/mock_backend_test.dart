import 'package:feeder_demo/mock_backend.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('mock backend completes one safe feed request', () async {
    final backend = MockFeederBackend();
    addTearDown(backend.dispose);

    final request = backend.feed();
    expect(backend.feeding, isTrue);

    await request;
    expect(backend.feeding, isFalse);
    expect(backend.scenario, DemoScenario.success);
    expect(backend.activity, contains('Đã cho ăn thành công · 40 g'));
  });

  test('offline mock backend rejects feed without activity', () async {
    final backend = MockFeederBackend();
    addTearDown(backend.dispose);
    backend.setScenario(DemoScenario.offline);

    await backend.feed();

    expect(backend.feeding, isFalse);
    expect(backend.activity, isEmpty);
  });
}
