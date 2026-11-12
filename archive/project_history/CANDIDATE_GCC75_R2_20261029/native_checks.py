"""Python3.6+ shared FILE-ONLY checks for Windows and owner ARM64 builds."""
from __future__ import print_function
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def replay_checks(exe,out,run):
    r1=[json.loads(s) for s in (ROOT/'fixtures/r1_quad_reports.log').read_text().splitlines() if s.startswith('{')]
    r2=json.loads((ROOT/'fixtures/synthetic_wire.json').read_text())['report']
    if len(r1)!=2:raise ValueError('R1 full-report fixture missing')
    compact=lambda x:json.dumps(x,separators=(',',':'))
    tested=[]
    def check(name,lines,chunk,accepted,rejected=0,oversized=0):
        path=out/(name+'.input')
        with path.open('xb') as f:f.write(('\n'.join(lines)+'\n').encode())
        rows=[json.loads(s) for s in run([exe,path,chunk],name).splitlines()]
        summary=rows[-1]
        if (summary['accepted'],summary['rejected'],summary['oversized'])!=(accepted,rejected,oversized):raise ValueError('parser counts mismatch: '+name)
        if summary['transmitted_commands'] is not False or summary['physical_pass'] is not False:raise ValueError('unsafe replay claim')
        tested.append(name);return rows
    for n in (1,7,127,1024,2048,8192):check('r1_fragment_'+str(n),[compact(v) for v in r1],n,2)
    line=compact(r2)
    if not 4096<len(line)<8192:raise ValueError('expected full R2 report >old4096 limit')
    for n in (1,7,127,8192):
        rows=check('r2_fragment_'+str(n),[line],n,1);t=rows[0]['telemetry']
        if t['mode']!='diag_current_hardware' or t['diagnostic_profile']!='diag_four_ultrasonic' or len(t['ultrasonic'])!=4:raise ValueError('wire/profile contract changed')
        if t['sensors']['buzzer']['capability'] is not False:raise ValueError('buzzer unexpectedly enabled')
    boundary=line+' '*(8192-len(line))
    check('boundary_8192',[boundary],127,1)
    check('oversized_8193',[boundary+' '],127,0,oversized=1)
    mutations=[]
    for key,value in (('mode','diag_four_ultrasonic'),('kit_profile','OTHER'),('telemetry_schema_version',3)):
        x=json.loads(line);x[key]=value;mutations.append(x)
    x=json.loads(line);del x['weight'];mutations.append(x)
    x=json.loads(line);del x['current_hardware']['manual_button_request_count'];mutations.append(x)
    x=json.loads(line);x['motion_valid']=False;mutations.append(x)
    x=json.loads(line);x['current_hardware']['pump_armed']=True;mutations.append(x)
    for sid in ('HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'):
        x=json.loads(line);x['ultrasonic'][sid]['echo_gpio']=6;mutations.append(x)
    for n,x in enumerate(mutations):check('reject_'+str(n),[compact(x)],7,0,rejected=1)
    check('duplicate_key',['{"mode":"HX711_REFERENCE",'+line[1:]],7,0,rejected=1)
    check('malformed',[line[:-8]],7,0,rejected=1)
    bad=json.loads(line);bad['current_hardware']['pump_armed']=True
    rows=check('unsafe_latch',[compact(bad),line],7,1,rejected=1)
    if rows[-1]['health_before_file_close']!='ESP32_BAD_TELEMETRY':raise ValueError('unsafe latch cleared')
    if len(tested)!=26:raise ValueError('missing parser checks')
    return tested

def collect_program_results(out,exe_suffix,run):
    exe=lambda name:out/(name+exe_suffix)
    food=run([exe('test_food_roi')],'food_roi_tests')
    if 'FOOD_ROI_PASS groups=10 checks=115 ' not in food:raise ValueError('FOOD_ROI regression failed')
    session=run([exe('test_session')],'session_tests')
    if 'DIAGNOSTIC_SESSION_PASS checks=17 ' not in session:raise ValueError('session regression failed')
    text=run([exe('logic_tests')],'logic_tests')
    m=re.search(r'OFFLINE_LOGIC_PASS groups=(\d+) checks=(\d+)',text)
    if not m:raise ValueError('logic summary missing')
    old_results=[json.loads(s[len('SIM_FEED_RESULT '):]) for s in text.splitlines() if s.startswith('SIM_FEED_RESULT ')]
    write_json(out/'fixtures/dispense_outcomes.json',{v['scenario']:v for v in old_results})
    new=run([exe('dispense_regressions')],'r2_dispense_tests')
    m2=re.search(r'R2_DISPENSE_PASS cases=(\d+) checks=(\d+)',new)
    if not m2 or int(m2.group(1))!=16:raise ValueError('R2 dispense regressions incomplete')
    results=[json.loads(s[len('R2_FEED_RESULT '):]) for s in new.splitlines() if s.startswith('R2_FEED_RESULT ')]
    if len(results)!=16 or any(v['source']!='SIMULATED' or v['physical_pass'] is not False for v in results):raise ValueError('invalid simulation provenance')
    for v in results:
        if v['scenario'] in ('over_band','overshoot_36','direct_launch_36','masked_window_36') and (v['state']!='FAULT' or v['reason']!='TARGET_OVERSHOOT'):raise ValueError('overshoot reported as success')
    write_json(out/'fixtures/r2_dispense_outcomes.json',{v['scenario']:v for v in results})
    timeline=[json.loads(s) for s in run([exe('timeline_probe'),ROOT/'fixtures/synthetic_wire.jsonl'],'timeline_tests').splitlines()]
    if [v['health'] for v in timeline]!=['ESP32_CONNECTED','ESP32_STALE','ESP32_DISCONNECTED','ESP32_STALE','ESP32_CONNECTED','ESP32_BAD_TELEMETRY']:raise ValueError('timeline health regression')
    write_json(out/'fixtures/session_timeline.json',timeline)
    parser=replay_checks(exe('parser_replay'),out,run)
    return {'food_roi':{'groups':10,'checks':115},'session_checks':17,
            'inherited_logic':{'groups':int(m.group(1)),'checks':int(m.group(2))},
            'r2_dispense':{'cases':int(m2.group(1)),'checks':int(m2.group(2))},
            'timeline_cases':len(timeline),'parser_cases':parser}
