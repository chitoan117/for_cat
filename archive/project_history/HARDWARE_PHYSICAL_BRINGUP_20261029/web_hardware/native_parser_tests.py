"""Real C++14/json-c parser+framer on Windows, mutations of FULL firmware fixtures.
Not ARM64 acceptance. File replay only: never opens any target device or database.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent;KIT=HERE.parent
EXE=HERE/'native_parser/parser_replay.exe'
def fixture():
    return [json.loads(s) for s in (KIT/'test_output/quad_firmware_loop_test.log').read_text().splitlines() if s.startswith('{')]
def replay(lines,tmp,chunk=1024):
    capture=tmp/'capture.log';capture.write_bytes(('\n'.join(lines)+'\n').encode())
    p=subprocess.run([str(EXE),str(capture),str(chunk)],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    rows=[json.loads(s) for s in p.stdout.splitlines()]
    return rows
def rejected(value,tmp):
    result=replay([json.dumps(value,separators=(',',':'))],tmp)
    assert result[-1]['accepted']==0 and result[-1]['rejected']==1
    assert result[0]['health']=='ESP32_BAD_TELEMETRY'
def test_full_released_reports_preserve_wire_mode_and_kit_identity(tmp_path):
    lines=[json.dumps(x,separators=(',',':')) for x in fixture()]
    assert all(len(s)>4096 for s in lines)
    for chunk in (1,7,127,1024,2048,8192):
        rows=replay(lines,tmp_path,chunk)
        assert rows[-1]['accepted']==2 and rows[-1]['oversized']==0
        normalized=rows[0]['telemetry'];assert normalized['mode']=='diag_current_hardware'
        assert normalized['wire_mode']=='diag_current_hardware' and normalized['diagnostic_profile']=='diag_four_ultrasonic'
        assert len(normalized['ultrasonic'])==4 and normalized['sensors']['buzzer']['capability'] is False
        assert normalized['sensors']['oled']['address']=='0x3c' and type(normalized['sensors']['oled']['initialized']) is bool
        assert normalized['sensors']['button']['pressed']==fixture()[0]['current_hardware']['button_pressed']
def test_exact8192_accepted_8193_dropped_no_truncation(tmp_path):
    s=json.dumps(fixture()[0],separators=(',',':'));line=s+' '*(8192-len(s))
    assert replay([line],tmp_path)[-1]['accepted']==1
    r=replay([line+' '],tmp_path);assert r[-1]['accepted']==0 and r[-1]['oversized']==1 and r[-1]['health_before_file_close']=='ESP32_BAD_TELEMETRY'
def test_modes_and_identity_must_not_be_guessed(tmp_path):
    for mode in ('HX711_REFERENCE','diag_four_ultrasonic','diag_all_sensors','diag_servo_bench','diag_pump_bench'):
        x=copy.deepcopy(fixture()[0]);x['mode']=mode;rejected(x,tmp_path)
    for key,value in [('kit_profile','HX711_REFERENCE'),('kit_firmware_id','UNKNOWN'),('ultrasonic_schema_version',2),('telemetry_schema_version',1),('voltage_physically_verified',True)]:
        x=copy.deepcopy(fixture()[0]);x[key]=value;rejected(x,tmp_path)
def test_required_fields_and_types(tmp_path):
    for key in ('ultrasonic','weight','current_hardware','kit_profile','motion_valid','kit_firmware_id'):
        x=copy.deepcopy(fixture()[0]);del x[key];rejected(x,tmp_path)
    for key,value in [('hx711_installed',1),('hardware_verified',True),('motion_valid','false'),('monotonic_ms',-1)]:
        x=copy.deepcopy(fixture()[0]);x[key]=value;rejected(x,tmp_path)
    x=copy.deepcopy(fixture()[0]);del x['current_hardware']['manual_button_request_count'];rejected(x,tmp_path)
def test_every_safety_guard_fail_closed(tmp_path):
    for key in ('servo_armed','pump_armed','auto_feed','auto_water'):
        x=copy.deepcopy(fixture()[0]);x['current_hardware'][key]=True;rejected(x,tmp_path)
    for key,value in [('actuator_outputs_enabled',1),('physical_pump_on',True)]:
        x=copy.deepcopy(fixture()[0]);x[key]=value;rejected(x,tmp_path)
    x=copy.deepcopy(fixture()[0]);x['manual_buzzer_capability']={};rejected(x,tmp_path)
def test_unknown_or_bad_safety_field_is_not_a_valid_frame(tmp_path):
    for key in ('servo_armed','pump_armed','auto_feed','auto_water','servo_state','pump_state'):
        x=copy.deepcopy(fixture()[0]);del x['current_hardware'][key];rejected(x,tmp_path)
def test_channel_identity_invalid_ranges_null_and_measurement_state(tmp_path):
    for sensor in ('HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'):
        x=copy.deepcopy(fixture()[0]);x['ultrasonic'][sensor]['echo_gpio']=6;rejected(x,tmp_path)
        x=copy.deepcopy(fixture()[0]);x['ultrasonic'][sensor]['distance_cm']=0;rejected(x,tmp_path)
        x=copy.deepcopy(fixture()[0]);x['ultrasonic'][sensor]['valid']=True;rejected(x,tmp_path)
    x=copy.deepcopy(fixture()[0]);x['ultrasonic']['JSN_SR04T_2']['measurement_state']=False;rejected(x,tmp_path)
def test_pir_warmup_cannot_claim_stable_or_motion_valid(tmp_path):
    for change in ({'motion_valid':True},{'motion_stable':True},{'motion_quality':'GOOD'}):
        x=copy.deepcopy(fixture()[0]);x.update(change);rejected(x,tmp_path)
def test_hx_sentinels_and_no_fake_zero_or_grams(tmp_path):
    for raw in (0,-1,8388607,-8388608,99999999):
        x=copy.deepcopy(fixture()[0]);x['raw_counts']=raw;rejected(x,tmp_path)
    x=copy.deepcopy(fixture()[0]);x['weight'].update(valid=False,value_grams=35);rejected(x,tmp_path)
def test_button_timestamp_and_oled_types(tmp_path):
    x=copy.deepcopy(fixture()[0]);x['current_hardware']['button_gpio']=6;rejected(x,tmp_path)
    x=copy.deepcopy(fixture()[0]);x['current_hardware']['oled_initialized']='yes';rejected(x,tmp_path)
def test_duplicate_keys_json_garbage_and_depth(tmp_path):
    s=json.dumps(fixture()[0],separators=(',',':'))
    for line in ('{"mode":"HX711_REFERENCE",'+s[1:],s+'{}','{"broken":',s.replace('"hardware_verified":false','"hardware_verified":NaN'),'{"deep":'+'['*20+'0'+']'*20+'}'):
        r=replay([line],tmp_path);assert r[-1]['accepted']==0
def test_unsafe_latch_not_cleared_by_later_good_frame(tmp_path):
    good=json.dumps(fixture()[0],separators=(',',':'));bad=copy.deepcopy(fixture()[0]);bad['current_hardware']['servo_armed']=True
    r=replay([json.dumps(bad,separators=(',',':')),good],tmp_path)
    assert r[-1]['health_before_file_close']=='ESP32_BAD_TELEMETRY' and r[-1]['transmitted_commands'] is False
