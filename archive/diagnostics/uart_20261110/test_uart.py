from pathlib import Path
from unittest.mock import patch
import importlib.util,sys,unittest
sys.path.append('/home/toan/for_cat/jetson/tools')
spec=importlib.util.spec_from_file_location('uart_candidate',Path(__file__).parent/'fc_live_bridge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Fake:
 def __init__(self,hardware):self.hardware=hardware;self.touched=[]
 def __setattr__(self,name,value):
  if name in ('dtr','rts'):
   if self.hardware:raise AssertionError('Hardware UART modem lines must not be toggled')
   self.touched.append((name,value))
  object.__setattr__(self,name,value)
class Tests(unittest.TestCase):
 def test_explicit_uart_wins_even_with_usb_connected(self):
  with patch.dict(m.os.environ,{'FORCAT_ESP32_PORT':'/dev/ttyTHS1'}),patch.object(m.Path,'is_char_device',return_value=True),patch.object(m.glob,'glob',return_value=['/dev/ttyACM0']):
   self.assertEqual(m.find_serial_device(),'/dev/ttyTHS1')
 def test_explicit_unavailable_uart_never_falls_back_to_usb(self):
  with patch.dict(m.os.environ,{'FORCAT_ESP32_PORT':'/dev/ttyTHS1'}),patch.object(m.Path,'is_char_device',return_value=False),patch.object(m.glob,'glob',return_value=['/dev/ttyACM0']):
   self.assertIsNone(m.find_serial_device())
 def test_default_usb_discovery_is_preserved(self):
  with patch.dict(m.os.environ,{'FORCAT_ESP32_PORT':''}),patch.object(m.glob,'glob',side_effect=[[],['/dev/ttyACM0']]):
   self.assertEqual(m.find_serial_device(),'/dev/ttyACM0')
 def test_hardware_uart_no_modem_line_toggles(self):
  fake=Fake(True)
  with patch.object(m.serial,'Serial',return_value=fake) as create:
   self.assertIs(m.open_serial_device('/dev/ttyTHS1'),fake)
   self.assertEqual(create.call_args.kwargs['baudrate'],115200)
   self.assertFalse(create.call_args.kwargs['rtscts'])
 def test_legacy_usb_line_setup_is_preserved(self):
  fake=Fake(False)
  with patch.object(m.serial,'Serial',return_value=fake):m.open_serial_device('/dev/ttyACM0')
  self.assertEqual(fake.touched,[('dtr',False),('rts',False)])
if __name__=='__main__':unittest.main(verbosity=2)
