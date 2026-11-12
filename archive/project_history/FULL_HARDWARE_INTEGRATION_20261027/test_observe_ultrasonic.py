import unittest
import os
from observe_ultrasonic import assess,command_bytes,summarize,DiagnosticPort,LineBuffer,Observer,json_stream,hx_fit_review

def rows(values,state='HEALTHY'):
    return [{'distance_cm':v,'valid':v is not None,'state':state,'timeout':state=='TIMEOUT','stale':False,'last_update':i*1000,'sample_age_ms':100,'timeout_count':0} for i,v in enumerate(values)]

class EvidenceTests(unittest.TestCase):
    def test_load_response_review_never_converts_counts_to_grams(self):
        points=[{'phase':'fit','mass_g':mass,'point_id':str(mass),'stats':{'mean_raw':mean,'raw_min_all':mean-10,'raw_max_all':mean+10,'spread_counts':20}} for mass,mean in ((0,-1000),(5,-6000))]
        result=hx_fit_review(points);self.assertTrue(result['basic_raw_load_response_observed']);self.assertIsNone(result['grams']);self.assertFalse(result['factor_computed'])
        self.assertEqual(result['fit_points'][1]['delta_from_zero_counts'],-5000)
        points[1]['stats']=points[0]['stats'].copy();self.assertFalse(hx_fit_review(points)['basic_raw_load_response_observed'])
    def test_calibration_tool_stream_preserves_settling_and_final_point(self):
        values=json_stream('{"phase":"SETTLING"}\n{\n "point_id":"synthetic", "grams":null\n}\n')
        self.assertEqual(len(values),2);self.assertEqual(values[-1]['point_id'],'synthetic');self.assertIsNone(values[-1]['grams'])
    def test_evidence_never_silently_overwritten(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            observer=Observer(Path(folder));one=observer.save('scheduler_g60',{'guard_ms':60})
            two=observer.save('scheduler_g80',{'guard_ms':80})
            self.assertNotEqual(one,two)
            with self.assertRaises(FileExistsError):observer.save('scheduler_g60',{'guard_ms':100})
    def test_split_json_and_crlf_preserve_non_newline_bytes(self):
        f=LineBuffer();lines=[]
        for chunk in (b'{"mode":',b'"fixture"}\r',b'\nACK\n'):
            lines.extend(f.feed(chunk))
        self.assertEqual(lines,[b'{"mode":"fixture"}',b'ACK'])
    def test_framer_oversize_discards_and_recovers(self):
        f=LineBuffer();self.assertEqual(f.feed(b'x'*5000+b'\n{"next":1}\n'),[b'{"next":1}'])
        self.assertEqual(f.oversized,1)
    @unittest.skipUnless(os.name=='posix','Linux PTY only; no real device')
    def test_diagnostic_adapter_roundtrip_on_synthetic_pty(self):
        import pty,select,termios
        master,slave=pty.openpty();device=os.ttyname(slave)
        try:
            with DiagnosticPort(device) as port:
                os.write(master,b'fixture-only\n')
                self.assertTrue(select.select([port.fileno()],[],[],1)[0])
                self.assertEqual(port.read(64),b'fixture-only\n')
                port.write(command_bytes('ultra-select jsn1 CONFIRM'));self.assertTrue(select.select([master],[],[],1)[0])
                self.assertEqual(os.read(master,64),b'ultra-select jsn1 CONFIRM\n')
                self.assertFalse(termios.tcgetattr(port.fileno())[2]&termios.HUPCL)
        finally:os.close(master);os.close(slave)
    def test_sensor_only_command_whitelist(self):
        self.assertEqual(command_bytes('ultra-select jsn1 CONFIRM'),b'ultra-select jsn1 CONFIRM\n')
        self.assertEqual(command_bytes('ultra-guard 100 CONFIRM'),b'ultra-guard 100 CONFIRM\n')
        for bad in ('SERVO OPEN','PUMP ON','tare 5','ultra-guard 50 CONFIRM','ultra-guard 1000 CONFIRM','ultra-select bogus CONFIRM','ultra-select hc1 CONFIRM\nSERVO OPEN'):
            with self.assertRaises(ValueError):command_bytes(bad)
    def test_no_null_or_history_substitution(self):
        data=rows([None]*24,'TIMEOUT')
        for row in data:row['last_valid_distance_cm']=20
        stats=summarize(data);self.assertIsNone(stats['mean_cm']);self.assertEqual(stats['valid_count'],0)
        result=assess('jsn1',stats,20);self.assertEqual(result['reason'],'RANGE_LIMIT_SUSPECTED');self.assertNotEqual(result['result'],'PHYSICAL_PASS')
    def test_finite_valid_range_only(self):
        stats=summarize(rows([0,-1,float('nan'),401,None]+[20]*19));self.assertEqual(stats['valid_count'],19)
    def test_majority_healthy_bench(self):
        stats=summarize(rows([20+i%3*.1 for i in range(24)]));self.assertEqual(assess('hc2',stats,20)['result'],'PHYSICAL_PASS')
    def test_wrong_target_does_not_pass(self):
        stats=summarize(rows([40+i%2 for i in range(24)]));self.assertTrue(assess('jsn1',stats,20)['action_required'])
    def test_constant_needs_movement_proof(self):
        stats=summarize(rows([20]*24));self.assertEqual(assess('hc2',stats,20)['reason'],'CONSTANT_READING_NEEDS_MOVEMENT_PROOF')
    def test_random_jumps_not_passed(self):
        stats=summarize(rows([16,24]*12));self.assertEqual(assess('hc2',stats,20)['reason'],'UNSTABLE_OR_LARGE_JUMPS')
    def test_cache_duplicates_not_independent(self):
        data=rows([20+i%2 for i in range(24)])
        for row in data:row['last_update']=1000
        self.assertEqual(assess('hc2',summarize(data),20)['reason'],'INSUFFICIENT_INDEPENDENT_UPDATES')

if __name__=='__main__':unittest.main()
