import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jetson'))
import sender
import meal_report

def rows(first,g):
    return [dict(received_utc=f'2026-10-31T00:00:{i:02d}+00:00',device=dict(type='status',schema='fc-cr-test-1',boot=123,dose_id=1,cal_generation=1,
        food='A',baseline_g=0,dose_g=35,tare_counts=100,grams_per_count=.01,calibration_source='NVS_SENSORS_V2',healthy=True,calibrated=True,state='MEASURED_NEEDS_OWNER_CONFIRMATION',
        ms=first+i*250,sample_ms=first+i*250,grams=g)) for i in range(4)]
class JetsonTests(unittest.TestCase):
    def test_frame_cross_language_vector(self):
        self.assertEqual(sender.frame(7,1,1000,'HB'),b'FC1 7 1 1000 HB*0B5E\n')
    def ai(self,**kwargs):
        x=dict(schema='fc-cat-1',source_seq=1,captured_monotonic_ns=1_000_000_000,label='CAT',confidence=.95);x.update(kwargs)
        return sender.inference(json.dumps(x),1_100_000_000,0)
    def test_ai_original_age(self):self.assertEqual(self.ai(),(1,100,950,1))
    def test_replayed_ai(self):
        with self.assertRaises(ValueError):sender.inference(json.dumps(dict(schema='fc-cat-1',source_seq=1,captured_monotonic_ns=1_000_000_000,label='CAT',confidence=.95)),1_100_000_000,1)
    def test_stale_future_ai(self):
        for t in (0,1_200_000_000):
            with self.assertRaises(ValueError):self.ai(captured_monotonic_ns=t)
    def test_bad_ai_confidence(self):
        for c in (float('nan'),-1,1.1,True):
            with self.assertRaises(ValueError):self.ai(confidence=c)
    def test_noncat(self):self.assertEqual(self.ai(label='DOG')[-1],0)
    def test_observation_no_preference_claim(self):
        r=meal_report.report(rows(1000,35),rows(10000,12),'trial-A','owner confirmed door closed; bowl untouched')
        self.assertEqual(r['apparent_removed_g'],23);self.assertIsNone(r['preference_conclusion']);self.assertFalse(r['consumption_proven'])
    def test_changed_boot_cal_dose(self):
        for key in ('boot','dose_id','cal_generation','tare_counts','grams_per_count'):
            end=rows(10000,12)
            for row in end:row['device'][key]+=1
            with self.assertRaises(ValueError):meal_report.report(rows(1000,35),end,'m','n')
    def test_frozen_scale(self):
        r=rows(1000,35)
        for row in r:row['device']['sample_ms']=1000
        with self.assertRaises(ValueError):meal_report.window(r)
    def test_unstable_or_stale(self):
        r=rows(1000,35);r[1]['device']['grams']=31
        with self.assertRaises(ValueError):meal_report.window(r)
        r=rows(1000,35);r[1]['device']['sample_ms']=0
        with self.assertRaises(ValueError):meal_report.window(r)
    def test_added_food_or_reversed_time(self):
        for end in (rows(10000,40),rows(500,12)):
            with self.assertRaises(ValueError):meal_report.report(rows(1000,35),end,'m','n')
    def test_pending_fault_not_measurement(self):
        r=rows(1000,35);r[0]['device']['state']='FAULT'
        with self.assertRaises(ValueError):meal_report.window(r)
if __name__=='__main__':unittest.main()
