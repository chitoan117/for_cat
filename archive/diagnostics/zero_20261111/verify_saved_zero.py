"""Read-only post-zero verification; reject inconsistent UART calibration fields."""
from pathlib import Path
import json,sqlite3,time,math,statistics,urllib.request
R=Path(__file__).resolve().parent;DB=Path('/home/toan/for_cat/jetson/data/events.db')
initial=json.loads((R/'zero_1794373816.json').read_text());ack=initial['save_ack']
assert ack['operation']=='rezero' and ack['ok'] is True and ack['saved'] is True
expected_factor=-0.000945082600219258
result={'saved_rezero_ack':ack,'initial_factor_from_single_uart_frame':initial['before']['grams_per_count'],'expected_previously_verified_factor':expected_factor,'uart_samples':[],'rejected_samples':[]}
seen=set();end=time.monotonic()+32
while time.monotonic()<end and len(result['uart_samples'])<10:
    with sqlite3.connect(DB,timeout=2) as db:s=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
    stamp=s['updated_monotonic_ms'];fc=s['telemetry']['fc_live']
    if stamp not in seen and 0<=time.monotonic()*1000-stamp<2500:
        seen.add(stamp);sample={k:fc.get(k) for k in ('tare_counts','grams_per_count','signed_g','grams','demo_exited')};sample['stamp']=stamp;sample['counters']=s['counters']
        factor=sample['grams_per_count'];tare=sample['tare_counts'];weight=sample['signed_g']
        consistent=all(type(x) in (int,float) and math.isfinite(x) for x in (factor,tare,weight)) and abs(factor-expected_factor)<1e-12 and abs(tare-ack['tare_counts'])<.001
        result['uart_samples' if consistent else 'rejected_samples'].append(sample)
    time.sleep(.2)
weights=[x['signed_g'] for x in result['uart_samples']]
if weights:result.update(min_g=min(weights),max_g=max(weights),mean_g=statistics.mean(weights),last_display_g=result['uart_samples'][-1]['grams'],tare_counts=result['uart_samples'][-1]['tare_counts'],grams_per_count=result['uart_samples'][-1]['grams_per_count'])
result['verified_near_zero']=len(weights)>=5 and max(abs(x) for x in weights)<=.3
result['uart_reliability_warning']=bool(result['rejected_samples']) or len(weights)<10
with urllib.request.urlopen('http://127.0.0.1:8000/api/status',timeout=5) as response:state=json.load(response)
result['api_connected']=state.get('esp32',{}).get('connected');result['api_grams']=state.get('grams')
(R/'saved_zero_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('uart_samples','rejected_samples')},indent=2));print('consistent_samples='+str(len(weights))+' rejected_samples='+str(len(result['rejected_samples'])))
