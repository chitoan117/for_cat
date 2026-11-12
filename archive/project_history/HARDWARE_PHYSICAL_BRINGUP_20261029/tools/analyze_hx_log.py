"""Analyze ALL valid signed HX measurements in an EXISTING log; no tare/refit.
Not an independent mass calibration or physical acceptance decision.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
def analyze(lines):
    values=[];invalid=0;ticks=[]
    for line in lines:
        try:data=json.loads(line)
        except ValueError:continue
        if not isinstance(data,dict):continue
        if data.get('kind')=='RX':data=data.get('json') or {}
        if data.get('mode')!='HX711_REFERENCE' or 'calibration_source' in data:continue
        value=data.get('measurement_grams')
        if data.get('valid') is not True or type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1000:invalid+=1;continue
        values.append(value);ticks.append(data.get('monotonic_ms'))
    result={'kind':'HX_EXISTING_LOG_ALL_SAMPLES','physical_pass':False,'calibration_authority':'NOT_PROMOTED',
            'sample_count':len(values),'invalid_count':invalid,'display_deadband_used_for_acceptance':False}
    if values:
        n=max(1,len(values)//2)
        result.update(first=values[0],last=values[-1],min=min(values),max=max(values),mean=statistics.mean(values),
            sigma=statistics.pstdev(values),range=max(values)-min(values),drift_half_means=statistics.mean(values[-n:])-statistics.mean(values[:n]),
            timestamp_continuity=all(type(t) is int for t in ticks) and all(b>a and b-a<=1500 for a,b in zip(ticks,ticks[1:])))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('existing_log',type=Path);a=p.parse_args()
    print(json.dumps(analyze(a.existing_log.read_text(encoding='utf-8',errors='replace').splitlines()),indent=2))
