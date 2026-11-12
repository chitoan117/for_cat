"""Synthetic mutations of the actual released firmware-loop report; file only."""
import copy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];KIT=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029'
def wire():
    x=[json.loads(s) for s in (KIT/'test_output/quad_firmware_loop_test.log').read_text().splitlines() if s.startswith('{')][-1]
    now=70000;x['monotonic_ms']=now
    for sid,cm in zip(('HC_SR04_1','HC_SR04_2','JSN_SR04T_1','JSN_SR04T_2'),(15,45,50,75)):
        x['ultrasonic'][sid].update(enabled=True,configured=True,wired=True,valid=True,timeout=False,stale=False,
            state='HEALTHY',distance_cm=cm,measurement_state='VALID_READING_NOT_PHYSICAL_PASS',
            last_update=now,sample_age_ms=0,last_valid_update=now,last_valid_distance_cm=cm)
    h=x['current_hardware'];h.update(approach_distance_valid=True,operational_water_distance_valid=True,
        oled_initialized=True,weight_calibrated=True,pir_transition_count=1,pir_last_transition_ms=now-500,
        button_press_count=1,manual_button_request_count=1,button_last_press_ms=now-40,
        button_pressed=True,button_raw_level=0,button_debounced_level=0)
    x.update(approach_distance_cm=15,water_distance_cm=50,approach_echo_ack=True,water_echo_ack=True,
        motion_input_configured=True,motion=True,motion_valid=True,motion_stable=True,motion_quality='VALID',
        raw_counts=-700123,weight_health='HEALTHY',oled_health='HEALTHY',button_health='HEALTHY')
    x['weight'].update(installed=True,valid=True,value_grams=34.981,sampled_at_ms=now,
        calibration_version=1,calibration_id='SIMULATED_ONLY_NOT_REAL_CALIBRATION')
    return x
def main():
    x=wire();base={'execution_context':'OFFLINE_TEST_ONLY','source':'SIMULATED','physical_pass':False,
                  'wire_mode':'diag_current_hardware','kit_profile':'diag_four_ultrasonic'}
    (HERE/'fixtures/synthetic_wire.json').write_text(json.dumps({**base,'report':x},indent=2)+'\n')
    (HERE/'fixtures/synthetic_wire.jsonl').write_bytes((json.dumps(x,separators=(',',':'))+'\n').encode())
    print('SIMULATED full wire fixture bytes='+str(len(json.dumps(x,separators=(',',':')))))
if __name__=='__main__':main()
