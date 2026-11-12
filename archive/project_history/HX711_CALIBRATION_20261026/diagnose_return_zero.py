"""Operator-directed raw load/unload diagnostic; never writes calibration or controls."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request

ROOT=Path('/home/toan/for_cat')
SID='hxcal_91ca4d57d8c24e5d92a3f063a8b01494'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    sys.path.insert(0,str(ROOT/'jetson'))
    from app.hx711_calibration import CalibrationStore,safe_bridge,binding,raw_statistics,point_quality,checksum
    store=CalibrationStore(ROOT/'jetson/data/events.db');session=store.session(SID)
    model=session['candidate']
    if model is None or store.active() is not None:raise ValueError('diagnostic requires the unactivated candidate')
    before_digest=session['candidate_digest'];before_round=session['verify_round'];before_count=len(store.points(SID))
    out=Path(session['evidence_dir'])/SID/('return_zero_cycle_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir()
    result={'scope':'OPERATOR_DIRECTED_DIAGNOSTIC_ONLY_NOT_FIT_OR_VERIFY','session_id':SID,
            'candidate_digest':before_digest,'phases':[],'calibration_written':False,
            'serial_opened':False,'actuator_commands_sent':False,'physical_gram_pass':False}
    result['actual_dispensed_grams']=None

    def source():
        with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/esp32/status',timeout=4) as response:body=json.load(response)
        raw=safe_bridge(body)
        if binding(body)!=model['binding']:raise ValueError('device binding changed')
        return raw,body

    def capture(label,seconds):
        records=[];last=None;first=None;start=time.monotonic();progress=10
        print(json.dumps({'phase':label,'seconds':seconds,'mode':'READ_ONLY_RAW_DIAGNOSTIC'}),flush=True)
        try:
            while time.monotonic()-start<seconds:
                raw,body=source();ms=body['telemetry']['monotonic_ms']
                if first is None:first=body
                if body['host_boot_id']!=first['host_boot_id'] or (last is not None and ms<last):raise ValueError('restart during phase')
                if ms!=last:records.append({'raw':raw,'device_ms':ms,'elapsed_s':time.monotonic()-start,'observed_at':body['last_received_at']})
                last=ms
                if time.monotonic()-start>=progress:
                    print(json.dumps({'phase':label,'elapsed_s':int(time.monotonic()-start),'unique_reports':len(records),'raw_latest':raw}),flush=True)
                    progress+=10
                time.sleep(.25)
        finally:
            phase={'label':label,'duration_s':time.monotonic()-start,'samples':records}
            if records:
                phase['mean_raw_all']=statistics.mean(p['raw'] for p in records)
                phase['diagnostic_mean_g']=(phase['mean_raw_all']-model['tare_offset_counts'])*model['grams_per_count']
            windows=[]
            for offset in range(0,int(seconds),30):
                values=[r for r in records if offset<=r['elapsed_s']<offset+30]
                if len(values)<2:continue
                try:
                    stats=raw_statistics(values,session['criteria'])
                    windows.append({'start_s':offset,'stats':stats,'diagnostic_grams':(stats['mean_raw']-model['tare_offset_counts'])*model['grams_per_count'],
                                    'quality':point_quality(stats,model['grams_per_count'],session['criteria'])})
                except ValueError as error:windows.append({'start_s':offset,'error':str(error)})
            phase['windows']=windows;result['phases'].append(phase)
            (out/'partial.json').write_text(json.dumps(result,indent=2))
        if len(records)<max(20,int(seconds*.7)):raise ValueError('not enough distinct telemetry reports')
        return phase

    try:
        input('BUOC1: KHay khong co qua can, giu nguyen co khi, bo tay ra. San sang thi nhan Enter: ')
        time.sleep(10);baseline=capture('BASELINE_UNLOADED',60)
        input('BUOC2: Dat20+10+5=35g vao giua khay, bo tay ra. San sang thi nhan Enter: ')
        time.sleep(10);loaded=capture('OPERATOR_REFERENCE35G',60)
        input('BUOC3: Lay ca3 qua can ra, GIU NGUYEN KHAY/DE. Bo tay ra roi nhan Enter: ')
        returned=capture('RETURN_UNLOADED',180)
        factor=model['grams_per_count'];base_raw=baseline['mean_raw_all']
        for window in returned['windows']:
            if 'stats' in window:window['return_difference_from_cycle_baseline_g']=(window['stats']['mean_raw']-base_raw)*factor
        result.update(status='DIAGNOSTIC_COMPLETE_REQUIRES_REVIEW',
                      estimated_added35g_delta=(loaded['mean_raw_all']-base_raw)*factor,
                      initial_zero_estimate_g=baseline['diagnostic_mean_g'],
                      final_return_difference_g=(returned['mean_raw_all']-base_raw)*factor)
    except BaseException as error:
        result.update(status='DIAGNOSTIC_INTERRUPTED',error=type(error).__name__+': '+str(error))
        raise
    finally:
        current=store.session(SID)
        result['candidate_unchanged']=current['candidate_digest']==before_digest==checksum(current['candidate'])
        result['verification_round_unchanged']=current['verify_round']==before_round
        result['reference_points_unchanged']=len(store.points(SID))==before_count
        result['active_calibration']=store.active() is not None
        path=out/'result.json';path.write_text(json.dumps(result,indent=2));(out/'result.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest())
        summary={k:v for k,v in result.items() if k!='phases'}
        summary['phase_windows']=[{'phase':p['label'],'windows':p['windows']} for p in result['phases']]
        summary['evidence']=str(path)
        print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
