import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'FULL_HARDWARE_INTEGRATION_20261027/payload/jetson'))
from app.device_state import Esp32StateReader

def test_warning_only_scope_is_accepted_without_feed_permission(tmp_path):
    path=tmp_path/'mock.db'
    good={'health':'ESP32_CONNECTED','serial_connected':True,'time_valid':False,'actuator_execution':False,
          'serial_tx_enabled':True,'serial_tx_scope':'DOG_WARNING_ONLY_NO_FEED_COMMANDS','dog_warning_tx_enabled':True,
          'feed_tx_enabled':False,'pump_tx_enabled':False,'host_boot_id':'fixture','updated_monotonic_ms':1000,
          'telemetry':{'safety':{'actuator_execution':False,'servo_armed':False,'pump_armed':False},'sensors':{}}}
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE esp32_latest(id INTEGER PRIMARY KEY,body TEXT)')
    def status(data):
        with sqlite3.connect(path) as db:db.execute('INSERT OR REPLACE INTO esp32_latest VALUES(1,?)',(json.dumps(data),))
        return Esp32StateReader(path,monotonic=lambda:1.1,boot_id='fixture').status()
    assert status(good)['telemetry_usable_now'] is True
    for delta in ({'feed_tx_enabled':True},{'pump_tx_enabled':True},{'dog_warning_tx_enabled':False},
                  {'serial_tx_scope':'FEED'},{'actuator_execution':True},{'feed_tx_enabled':0}):
        assert status({**good,**delta})['reader_error']=='ValueError'
    legacy={**good,'serial_tx_enabled':False}
    for name in ('serial_tx_scope','dog_warning_tx_enabled','feed_tx_enabled','pump_tx_enabled'):legacy.pop(name)
    assert status(legacy)['telemetry_usable_now'] is True
    assert status({**legacy,'feed_tx_enabled':True})['reader_error']=='ValueError'
