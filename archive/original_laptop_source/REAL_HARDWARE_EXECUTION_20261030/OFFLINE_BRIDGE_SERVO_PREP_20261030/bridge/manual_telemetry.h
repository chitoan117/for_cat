#pragma once
// Included inside namespace forcat after typed JSON helpers and UnsafeTelemetry.
// Accept only the exact V1 manual station contract, not a renamed legacy frame.
inline void validateManualStation(json_object* r,json_object* current) {
    if(text(r,"kit_firmware_id")!="FORCAT_MANUAL_STATION_20261030_V1" ||
       text(r,"kit_profile")!="diag_manual_station" || counter(r,"telemetry_schema_version")!=2 ||
       counter(r,"ultrasonic_schema_version")!=1 || text(r,"rtc_type")!="NONE" ||
       boolean(current,"rtc_detected") || boolean(r,"voltage_physically_verified"))
        throw std::invalid_argument("manual firmware identity/schema");
    auto m=field(r,"manual_station");
    if(!field(r,"ultrasonic") || !field(r,"weight") || !field(current,"manual_button_request_count"))
        throw std::invalid_argument("manual required sensor objects");
    json_object* unexpected=nullptr;
    if(json_object_object_get_ex(r,"manual_buzzer_capability",&unexpected))
        throw UnsafeTelemetry("UNREVIEWED_MANUAL_BUZZER_TX_CAPABILITY");
    if(counter(m,"schema_version")!=1 || !counter(m,"boot_nonce") || counter(m,"servo_gpio")!=6 ||
       counter(m,"pump_gpio")!=7 || counter(m,"buzzer_gpio")!=2)
        throw std::invalid_argument("manual schema/pin/boot contract");
    counter(m,"session");counter(m,"last_sequence");
    if(boolean(m,"automatic_execution") || counter(r,"automatic_actuator_outputs_enabled")!=0 ||
       boolean(current,"auto_feed") || boolean(current,"auto_water"))
        throw UnsafeTelemetry("MANUAL_AUTOMATIC_AUTHORITY_VIOLATION");
    if(boolean(m,"physical_pass") || boolean(m,"mechanical_close_verified"))
        throw std::invalid_argument("manual observation cannot grant physical acceptance");
    if(field(r,"physical_pump_on")!=nullptr)
        throw std::invalid_argument("manual has no physical pump feedback");
    const auto servo=text(m,"servo_state"),pump=text(m,"pump_state");
    if(!std::set<std::string>{"DISARMED","ARMED","MOVING","CLOSING","FAULT"}.count(servo) ||
       !std::set<std::string>{"DISARMED","ARMED","ON","FAULT"}.count(pump))
        throw std::invalid_argument("unknown manual output state");
    const bool sa=servo=="ARMED" || servo=="MOVING" || servo=="CLOSING";
    const bool pa=pump=="ARMED" || pump=="ON",ba=boolean(m,"buzzer_active");
    if(boolean(current,"servo_armed")!=sa || boolean(current,"pump_armed")!=pa ||
       text(current,"servo_state")!=servo || text(current,"pump_state")!=pump)
        throw UnsafeTelemetry("MANUAL_STATE_MIRROR_CONFLICT");
    if(static_cast<unsigned>(sa)+static_cast<unsigned>(pa)+static_cast<unsigned>(ba)>1)
        throw UnsafeTelemetry("MANUAL_OUTPUT_INTERLOCK_VIOLATION");
    const auto pulse=counter(m,"servo_pulse_us"),close=counter(m,"servo_close_us"),open=counter(m,"servo_open_us");
    if((sa && (pulse<1000 || pulse>2000)) || (!sa && pulse!=0))
        throw UnsafeTelemetry("MANUAL_PWM_STATE_CONFLICT");
    if((close || open) && (close<1000 || close>2000 || open<1000 || open>2000 || open==close ||
       (close>open?close-open:open-close)>100))throw UnsafeTelemetry("MANUAL_UNREVIEWED_TRAVEL");
    if(sa && (!close || !open))throw UnsafeTelemetry("MANUAL_UNCONFIGURED_PWM");
    if(counter(m,"servo_arms")>3 || counter(m,"pump_pulses")>3)
        throw UnsafeTelemetry("MANUAL_BUDGET_VIOLATION");
    auto off=field(m,"pump_off_level");
    if(!off || !json_object_is_type(off,json_type_int))throw std::invalid_argument("manual pump OFF integer");
    const auto level=json_object_get_int64(off);const bool supported=boolean(m,"pump_supported");
    if((supported && level!=0 && level!=1) || (!supported && level!=-1))
        throw UnsafeTelemetry("MANUAL_PUMP_POLARITY_CONFLICT");
    const bool commanded=boolean(m,"pump_commanded_on");
    if(commanded!=(pump=="ON") || (!supported && (pa || commanded || counter(m,"pump_pulses")!=0)))
        throw UnsafeTelemetry("MANUAL_INERT_OR_PUMP_STATE_VIOLATION");
    if(ba && !boolean(m,"buzzer_enabled"))throw UnsafeTelemetry("MANUAL_DISABLED_BUZZER_ACTIVE");
    const bool fault=boolean(m,"fault_latched");
    if((fault && (sa || pa || ba || counter(m,"session")!=0)) ||
       (!fault && (servo=="FAULT" || pump=="FAULT")))
        throw UnsafeTelemetry("MANUAL_FAULT_STATE_CONFLICT");
}

inline void normalizeManualStation(json_object* r,json_object* n,json_object* safety,json_object* sensors) {
    auto m=field(r,"manual_station");
    copy(n,"manual_station",r,"manual_station");
    put(n,"automatic_execution_ready",false);put(n,"closed_loop_feed_capability",false);
    put(n,"manual_observation_only",true);put(n,"bridge_serial_tx_enabled",false);
    // Zero global/automatic authority must not be misread as physical motor OFF.
    json_object_object_add(safety,"actuator_outputs_enabled",nullptr);
    integer(safety,"automatic_actuator_outputs_enabled",0);
    put(safety,"automatic_execution_ready",false);put(safety,"bridge_actuator_authority",false);
    put(safety,"fault_latched",boolean(m,"fault_latched"));
    json_object_object_add(safety,"physical_pump_on",nullptr);
    auto buzzer=field(sensors,"buzzer");
    put(buzzer,"capability",false);put(buzzer,"manual_test_supported_by_firmware",true);
    put(buzzer,"state",boolean(m,"buzzer_active")?"ACTIVE_REPORTED":boolean(m,"buzzer_enabled")?"IDLE_REPORTED":"DISABLED_REPORTED");
    put(buzzer,"state_is_wire_observation",true);put(buzzer,"physical_off_verified",false);
}
