"""Offline A/B observation from two stable log windows; never a preference verdict."""
import argparse
import json
import math
from pathlib import Path

def window(rows):
    if len(rows)<4:raise ValueError('Need at least four device observations per window')
    d=[r['device'] for r in rows]
    for x in d:
        if x.get('schema')!='fc-cr-test-1' or x.get('type')!='status' or not x['healthy'] or not x['calibrated'] or x['state']!='MEASURED_NEEDS_OWNER_CONFIRMATION':raise ValueError('Unqualified measurement/state')
        if not x['dose_id'] or not x['cal_generation']:raise ValueError('No dose/calibration provenance')
        if ((x['ms']-x['sample_ms'])&0xffffffff)>500:raise ValueError('Stale scale')
        if any(type(x[k]) not in (int,float) or not math.isfinite(x[k]) for k in ('grams','baseline_g','dose_g','tare_counts','grams_per_count')):raise ValueError('Missing/nonfinite mass/calibration')
        if x['grams_per_count']==0 or x['calibration_source'] not in ('NVS_SENSORS_V2','EXACT_REVIEWED_IMPORT'):raise ValueError('Missing calibration provenance')
    key=lambda x:tuple(x[k] for k in ('boot','dose_id','cal_generation','food','baseline_g','dose_g','tare_counts','grams_per_count','calibration_source'))
    if any(key(x)!=key(d[0]) for x in d):raise ValueError('Changed measurement context')
    if any(b['sample_ms']<=a['sample_ms'] for a,b in zip(d,d[1:])):raise ValueError('Repeated/reversed samples or clock wrap')
    if d[-1]['sample_ms']-d[0]['sample_ms']<200:raise ValueError('Window too short')
    weights=[x['grams'] for x in d]
    if max(weights)-min(weights)>1:raise ValueError('Unstable measurement window')
    return d[0],sum(weights)/len(weights),rows[0]['received_utc'],rows[-1]['received_utc']

def report(start,end,meal_id,notes):
    a,initial,at,_=window(start);b,remaining,_,bt=window(end)
    fields=('boot','dose_id','cal_generation','food','baseline_g','dose_g','tare_counts','grams_per_count','calibration_source')
    if any(a[k]!=b[k] for k in fields):raise ValueError('Different dose/calibration context')
    if b['sample_ms']<=start[-1]['device']['sample_ms']:raise ValueError('End precedes/overlaps start')
    if a['food'] not in ('A','B') or not 30<=a['dose_g']<=40:raise ValueError('Not an accepted labeled portion')
    initial_food=initial-a['baseline_g'];remaining_food=remaining-a['baseline_g']
    if remaining_food<0 or initial_food<0 or remaining_food>initial_food:raise ValueError('Mass addition/removal or negative remaining: inspect observation')
    return dict(schema='fc-meal-observation-1',meal_id=meal_id,food=a['food'],boot=a['boot'],dose_id=a['dose_id'],cal_generation=a['cal_generation'],
        tare_counts=a['tare_counts'],grams_per_count=a['grams_per_count'],calibration_source=a['calibration_source'],
        measured_dispensed_g=a['dose_g'],initial_observed_food_g=initial_food,remaining_observed_food_g=remaining_food,
        apparent_removed_g=initial_food-remaining_food,start_utc=at,end_utc=bt,notes=notes,
        identity='UNKNOWN_GENERIC_CAT',preference_conclusion=None,consumption_proven=False,
        limitations='Apparent removal may include spillage, bowl handling or other animals. Owner must confirm closure and controlled observation conditions.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--log',required=True);p.add_argument('--meal-id',required=True)
    p.add_argument('--start-lines',nargs=2,type=int,required=True,metavar=('FIRST','LAST'))
    p.add_argument('--end-lines',nargs=2,type=int,required=True,metavar=('FIRST','LAST'))
    p.add_argument('--notes',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    rows=[json.loads(s) for s in Path(a.log).read_text(encoding='utf-8').splitlines()]
    def get(bounds):
        first,last=bounds
        if not 1<=first<=last<=len(rows):raise ValueError('Invalid 1-based inclusive line range')
        return rows[first-1:last]
    result=report(get(a.start_lines),get(a.end_lines),a.meal_id,a.notes)
    with open(a.output,'x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
