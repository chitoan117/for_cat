from pathlib import Path
import importlib.util,json,sqlite3,sys,tempfile,unittest
sys.path.insert(0,'/home/toan/for_cat/jetson/tools')
spec=importlib.util.spec_from_file_location('without_pir',Path(__file__).with_name('fc_live_bridge.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Removal(unittest.TestCase):
    def test_legacy_motion_cannot_create_installed_pir(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'events.db'
            bridge=m.BridgeRunner(db)
            for legacy_level in (True,False,None):
                bridge.handle_status({'type':'status','ms':1000,'motion':legacy_level,'pir_configured':True},'/dev/ttyTHS1')
                with sqlite3.connect(db) as conn:
                    payload=json.loads(conn.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
                pir=payload['telemetry']['sensors']['pir']
                self.assertFalse(pir['configured'])
                self.assertIsNone(pir['motion'])
                self.assertIsNone(pir['transition_count'])
                self.assertEqual(pir['health'],'NOT_CONFIGURED')
if __name__=='__main__':unittest.main(verbosity=2)
