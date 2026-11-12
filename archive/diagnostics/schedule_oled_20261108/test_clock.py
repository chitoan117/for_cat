from pathlib import Path
import tempfile,unittest,types
import test_bridge

m=test_bridge.m

class ClockTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.path=Path(self.temp.name)/'clock.json'
        self.wall,self.mono,self.synced=100000.,100.,False
        m.time=types.SimpleNamespace(time=lambda:self.wall,monotonic=lambda:self.mono)
        self.g=m.SystemClockGate('boot-one',self.path,lambda:self.synced)

    def tearDown(self):self.temp.cleanup()

    def advance(self,seconds):self.wall+=seconds;self.mono+=seconds

    def test_stale_boot_is_invalid_until_sync(self):
        self.assertFalse(self.g.valid());self.synced=True
        self.advance(5);self.assertTrue(self.g.valid());self.assertTrue(self.path.exists())

    def test_offline_same_boot_restart_retains_confirmed_clock(self):
        self.synced=True;self.assertTrue(self.g.valid());self.synced=False
        self.advance(86400);self.assertTrue(self.g.valid())
        restarted=m.SystemClockGate('boot-one',self.path,lambda:False)
        self.assertTrue(restarted.valid())
        different_boot=m.SystemClockGate('boot-two',self.path,lambda:False)
        self.assertFalse(different_boot.valid())

    def test_clock_jump_revokes_trust_until_reconfirmed(self):
        self.synced=True;self.assertTrue(self.g.valid())
        self.wall+=86400;self.assertFalse(self.g.valid());self.assertFalse(self.path.exists())
        self.synced=False;self.advance(5);self.assertFalse(self.g.valid())
        self.synced=True;self.advance(5);self.assertTrue(self.g.valid())

    def test_restart_after_clock_jump_does_not_accept_old_marker(self):
        self.synced=True;self.assertTrue(self.g.valid())
        self.wall-=86400
        restarted=m.SystemClockGate('boot-one',self.path,lambda:False)
        self.assertFalse(restarted.valid())

    def test_probe_failure_is_false_and_throttled(self):
        calls=[];self.g.probe=lambda:calls.append(1) or False
        self.assertFalse(self.g.valid());self.advance(1);self.assertFalse(self.g.valid())
        self.assertEqual(len(calls),1);self.advance(4);self.g.valid();self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
