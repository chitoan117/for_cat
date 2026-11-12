from pathlib import Path
import ast,unittest
s=Path(__file__).with_name('fc_live_bridge.py').read_text()
node=next(n for n in ast.parse(s).body if isinstance(n,ast.ClassDef) and n.name=='SerialLineBuffer')
scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<tested-line-buffer>','exec'),scope)
Buffer=scope['SerialLineBuffer']
class Tests(unittest.TestCase):
    def test_status_fragments_and_timeout(self):
        b=Buffer();self.assertEqual(b.feed(b'{"type":"sta'),[])
        self.assertEqual(b.feed(b''),[])
        self.assertEqual(b.feed(b'tus","grams":0.6}\r\n'),['{"type":"status","grams":0.6}'])
    def test_multiple_records_and_split_unicode(self):
        b=Buffer();raw='mèo\n{"type":"hx_cal","saved":true}\n'.encode()
        output=[]
        for x in raw:output+=b.feed(bytes([x]))
        self.assertEqual(output,['mèo','{"type":"hx_cal","saved":true}'])
    def test_overlong_frame_resynchronizes_on_newline(self):
        b=Buffer();self.assertEqual(b.feed(b'x'*17000),[]);self.assertLessEqual(len(b.pending),16384)
        self.assertEqual(b.feed(b'bad_tail\nGOOD\n'),['GOOD'])
if __name__=='__main__':unittest.main(verbosity=2)
