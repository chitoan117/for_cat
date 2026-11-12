import 'package:web/web.dart' as web;
import 'pending_store_base.dart';

class BrowserPendingStore implements PendingStore {
  final String key;
  BrowserPendingStore(String subSource) : key = 'for_cat_flutter_preview_v1_$subSource';
  @override String? load() => web.window.localStorage.getItem(key);
  @override void save(String value) => web.window.localStorage.setItem(key, value);
  @override void clear() => web.window.localStorage.removeItem(key);
}
PendingStore createPendingStore(String subSource) => BrowserPendingStore(subSource);
