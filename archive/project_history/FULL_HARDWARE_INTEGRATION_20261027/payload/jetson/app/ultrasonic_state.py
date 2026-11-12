"""Four independent REAL channels. Owner wiring metadata is not a measurement."""
import json
import math
from pathlib import Path
import time

SPECS={
 'HC_SR04_1':('HC-SR04','CAT_APPROACH',12,13,'approach'),
 'HC_SR04_2':('HC-SR04','TBD',16,17,None),
 'JSN_SR04T_1':('JSN-SR04T','WATER_LEVEL',14,15,'water_operational'),
 'JSN_SR04T_2':('JSN-SR04T','TBD',18,10,None)}
STATES={'HEALTHY','TIMEOUT','STALE','UNKNOWN','NOT_WIRED','NOT_CONFIGURED','DISABLED'}

def load_inventory():
    try:
        data=json.loads((Path(__file__).resolve().parents[2]/'config/hardware_current.json').read_text())['ultrasonic_inventory']
        assert data['schema_version']==1
        for key,(kind,role,trig,echo,_) in SPECS.items():
            s=data[key]
            assert (s['type'],s['role'],s['trigger_gpio'],s['echo_gpio'])==(kind,role,trig,echo) and type(s['wired']) is bool
        return data
    except (OSError,ValueError,KeyError,AssertionError,TypeError):return {}

def unknown_channels(inventory=None):
    inventory=inventory or {}
    return {key:{'sensor_id':key,'type':kind,'role':role,'trigger_gpio':trig,'echo_gpio':echo,
      'wired':inventory.get(key,{}).get('wired'),'configured':None,'enabled':None,'distance_cm':None,
      'valid':False,'timeout':None,'stale':None,'state':'UNKNOWN','sample_age_ms':None,'last_update':None,
      'last_valid_distance_cm':None,'last_valid_update':None,'physical_verification':'NOT_TESTED','firmware_supported':None}
      for key,(kind,role,trig,echo,_) in SPECS.items()}

def validate_channels(channels):
    if not isinstance(channels,dict) or set(channels)!=set(SPECS):raise ValueError('ultrasonic identities')
    for key,(kind,role,trig,echo,_) in SPECS.items():
        s=channels[key]
        if not isinstance(s,dict) or (s.get('type'),s.get('role'),s.get('trigger_gpio'),s.get('echo_gpio'))!=(kind,role,trig,echo):raise ValueError('ultrasonic metadata')
        if s.get('state') not in STATES:raise ValueError('ultrasonic state')
        if any(type(s.get(k)) is not bool for k in ('wired','configured','enabled','valid','timeout','stale')):raise ValueError('ultrasonic flags')
        for k in ('last_update','last_valid_update','sample_age_ms','timeout_count'):
            v=s.get(k)
            if v is not None and (type(v) is not int or not 0<=v<=0xffffffff):raise ValueError('ultrasonic timestamp')
        if type(s.get('timeout_count')) is not int:raise ValueError('ultrasonic counter')
        for k in ('distance_cm','last_valid_distance_cm'):
            v=s.get(k)
            if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=400):raise ValueError('ultrasonic range')
        if s['valid']!=(s.get('distance_cm') is not None):raise ValueError('ultrasonic validity')
        if (s.get('last_update') is None)!=(s.get('sample_age_ms') is None):raise ValueError('ultrasonic age pair')
        if (s.get('last_valid_update') is None)!=(s.get('last_valid_distance_cm') is None):raise ValueError('ultrasonic history pair')
        if s['valid'] and (not all(s[k] for k in ('enabled','configured','wired')) or s['timeout'] or s['stale'] or s['state']!='HEALTHY' or s.get('sample_age_ms') is None or s['sample_age_ms']>2000):raise ValueError('ultrasonic healthy flags')
        if (s['state']=='HEALTHY')!=s['valid']:raise ValueError('ultrasonic healthy state')
        if s['state']=='TIMEOUT' and not s['timeout'] or s['state']=='STALE' and not s['stale'] or s['state']=='DISABLED' and s['enabled']:raise ValueError('ultrasonic state/flag mismatch')

def channels_view(bridge,inventory=None,clock=time.monotonic):
    result=unknown_channels(inventory)
    fresh=bridge.get('telemetry_usable_now') is True
    telemetry=bridge.get('telemetry') or {};raw=telemetry.get('ultrasonic')
    if raw is not None:
        validate_channels(raw)
        stamp=bridge.get('last_rx_monotonic_ms',bridge.get('updated_monotonic_ms'))
        elapsed=clock()*1000-stamp if type(stamp) in (int,float) and math.isfinite(stamp) else None
        if elapsed is not None and elapsed<0:elapsed=None
        for key in SPECS:
            s={**result[key],**raw[key],'firmware_supported':True,'physical_verification':'NOT_TESTED'}
            age=raw[key]['sample_age_ms'];age=age+int(elapsed) if age is not None and elapsed is not None else None
            s['sample_age_ms']=age
            if not fresh or elapsed is None:
                s.update(distance_cm=None,valid=False,timeout=None,stale=bridge.get('health')=='ESP32_STALE',state='STALE' if bridge.get('health')=='ESP32_STALE' else 'UNKNOWN')
            elif s['enabled'] and age is not None and age>2000:
                s.update(distance_cm=None,valid=False,stale=True,state='STALE')
            result[key]=s
        return result
    # Older firmware remains usable, but #2 cannot be inferred from inventory %.
    for key,(_,_,_,_,alias) in SPECS.items():
        s=result[key];s['firmware_supported']=False
        if not fresh:continue
        if alias:
            old=(telemetry.get('sensors') or {}).get(alias,{})
            enabled=old.get('echo_ack');s.update(configured=old.get('configured'),enabled=enabled,timeout_count=old.get('timeout_count'),source='LEGACY_ALIAS_NO_SAMPLE_TIMESTAMP')
            if enabled is False:s['state']='DISABLED'
            elif old.get('distance_valid') is True:
                s.update(distance_cm=old.get('distance_cm'),valid=True,state='HEALTHY',timeout=False,stale=False)
            elif old.get('timeout_count',0)>0:s.update(state='TIMEOUT',timeout=True)
        else:s['reason']='FIRMWARE_EXTENSION_NOT_AVAILABLE_FLASH_REQUIRED'
    return result
