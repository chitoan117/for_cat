abstract class PendingStore {
  String? load();
  void save(String value);
  void clear();
}

class MemoryPendingStore implements PendingStore {
  String? value;
  @override
  String? load() => value;
  @override
  void save(String next) => value = next;
  @override
  void clear() => value = null;
}
