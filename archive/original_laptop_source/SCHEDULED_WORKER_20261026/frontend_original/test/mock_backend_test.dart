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
    expect(backend.activity, contains('MOCK · request DRY RUN 35 g · không cấp thức ăn'));
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
