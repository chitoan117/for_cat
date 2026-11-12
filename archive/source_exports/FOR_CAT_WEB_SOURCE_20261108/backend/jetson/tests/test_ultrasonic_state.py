import copy
import json
import pytest
from app.ultrasonic_state import SPECS,channels_view,validate_channels

def channels():
    return {key:{'type':kind,'role':role,'trigger_gpio':trig,'echo_gpio':echo,
       'wired':True,'configured':True,'enabled':True,'valid':True,'timeout':False,'stale':False,'state':'HEALTHY',
       'distance_cm':30+i*10,'sample_age_ms':0,'last_update':1000,'last_valid_distance_cm':30+i*10,'last_valid_update':1000,'timeout_count':0}
       for i,(key,(kind,role,trig,echo,_)) in enumerate(SPECS.items())}
def bridge():return {'health':'ESP32_CONNECTED','telemetry_usable_now':True,'last_rx_monotonic_ms':100000,'telemetry':{'ultrasonic':channels(),'ultrasonic_schema_version':1}}

def test_four_distinct_channels_and_receipt_age_without_overwrite():
    b=bridge();v=channels_view(b,clock=lambda:100.25)
    assert [v[k]['distance_cm'] for k in SPECS]==[30,40,50,60]
    assert all(s['sample_age_ms']==250 and s['state']=='HEALTHY' for s in v.values())
    assert b['telemetry']['ultrasonic']['HC_SR04_1']['sample_age_ms']==0

@pytest.mark.parametrize('health,fresh',[('ESP32_STALE',False),('ESP32_DISCONNECTED',False),('ESP32_CONNECTED',True)])
def test_stale_or_lost_channel_hides_current_keeps_historical(health,fresh):
    b=bridge();b.update(health=health,telemetry_usable_now=fresh)
    v=channels_view(b,clock=lambda:103)
    assert all(s['distance_cm'] is None and s['valid'] is False and s['last_valid_distance_cm'] is not None for s in v.values())
    assert v['HC_SR04_1']['state']==('UNKNOWN' if health=='ESP32_DISCONNECTED' else 'STALE')

def test_timeout_keeps_history_and_never_zero_distance():
    b=bridge();s=b['telemetry']['ultrasonic']['HC_SR04_2'];s.update(valid=False,distance_cm=None,timeout=True,state='TIMEOUT',timeout_count=3)
    v=channels_view(b,clock=lambda:100.1);assert v['HC_SR04_2']['state']=='TIMEOUT' and v['HC_SR04_2']['distance_cm'] is None
    assert v['HC_SR04_1']['distance_cm']==30

@pytest.mark.parametrize('change',[{'distance_cm':0},{'enabled':False},{'sample_age_ms':3000},{'trigger_gpio':6},{'last_valid_update':None},{'valid':'true'}])
def test_invalid_normalized_cache_rejected(change):
    values=channels();values['HC_SR04_1'].update(change)
    with pytest.raises(ValueError):validate_channels(values)

def test_legacy_telemetry_no_extension_never_fabricates_second_sensors():
    b=bridge();b['telemetry']={'sensors':{'approach':{'configured':False,'echo_ack':False,'distance_valid':False}}}
    inventory={key:{'wired':True} for key in SPECS}
    v=channels_view(b,inventory,clock=lambda:100)
    assert v['HC_SR04_1']['state']=='DISABLED'
    for key in ('HC_SR04_2','JSN_SR04T_2'):
        assert v[key]['wired'] is True and v[key]['state']=='UNKNOWN' and v[key]['distance_cm'] is None and v[key]['firmware_supported'] is False

@pytest.mark.parametrize('stamp,update,age',[(1000,900,0),(1000,1100,100),(1000,True,0),('bad',1000,0)])
def test_cache_timestamp_contract_is_validated(stamp,update,age):
    from app.device_state import validate_cached_telemetry
    values=channels();values['HC_SR04_1'].update(last_update=update,sample_age_ms=age)
    with pytest.raises(ValueError):validate_cached_telemetry({'monotonic_ms':stamp,'ultrasonic_schema_version':1,'ultrasonic':values})

def test_additive_real_rest_ws_sqlite_and_legacy_aliases(tmp_path):
    import sqlite3,time
    from contextlib import closing
    from fastapi.testclient import TestClient
    from app.main import create_app
    from test_system_state import store
    dbpath=tmp_path/'synthetic_only.db';store(dbpath)
    with closing(sqlite3.connect(dbpath)) as db:
        data=json.loads(db.execute('SELECT body FROM esp32_latest').fetchone()[0]);data['telemetry'].update(ultrasonic=channels(),ultrasonic_schema_version=1)
        data['last_rx_monotonic_ms']=time.monotonic()*1000
        db.execute('UPDATE esp32_latest SET body=?',(json.dumps(data),));db.commit()
    with TestClient(create_app(db_path=dbpath)) as client:
        s=client.get('/api/status').json();assert len(s['ultrasonic'])==4
        assert s['ultrasonic']['HC_SR04_2']['distance_cm']==40
        assert s['approach']['distance_cm']==30 and s['water_operational']['distance_cm']==50
        with client.websocket_connect('/api/ws/state') as ws:assert ws.receive_json()['ultrasonic']['JSN_SR04T_2']['distance_cm']==60
