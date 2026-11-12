#include <Arduino.h>
#include <Preferences.h>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "m4/ledc_servo.h"
#include "feed_link.h"
#include "dog_warning_protocol.h"
#include "servo_bus.h"
#ifndef FORCAT_DUAL_STATION
#error "Explicit dual station required"
#endif
#if defined(ESP_PLATFORM) && defined(MANUAL_STATION_HOST_TEST)
#error "Host test nonce is not real firmware"
#endif
namespace {
m4::LedcServoOutput dual_driver;
ExclusiveServoBus dual_servo_bus(dual_driver);
void hybridTelemetry();bool hybridFeedByte(uint8_t byte,uint32_t now);void hybridAbort();
}
// Exactly one manual parser/driver station: setup/loop names are fork-local.
#include "manual_station.cpp"
namespace {
class DualJournal:public m4::dispense_bench::Journal {
 public:
    bool write(bool,uint32_t)override{return false;} // INERT: cannot initialize or clear NVS journal
};
class DualSink:public feed_link::Sink {
 public:
    void emit(uint32_t id,uint8_t op,const uint8_t* p,uint16_t n)override{
        uint8_t b[uart_v1::MAX_FRAME];size_t size=0;
        if(uart_v1::encode(id,op,p,n,b,sizeof(b),size))protocolSerial().write(b,size);
    }
};
class DualWarning:public feed_link::Warning {public:bool pulse(uint32_t)override{return false;}};
DualJournal feed_journal;DualSink feed_sink;DualWarning feed_warning;
// Physical enable is hard-false, not remotely toggleable. The shared bus also
// rejects competing owners; future active feed requires an actual closure source.
feed_link::Endpoint feed_endpoint(dual_servo_bus.feed(),feed_journal,feed_sink,feed_warning,false);
dog_wire::Parser feed_parser;
void hybridTelemetry(){
    protocolSerial().printf("\"feed_link\":{\"schema_version\":1,\"physical_enable\":false,\"closure_provider_available\":false,\"servo_owner\":\"%s\"},",dual_servo_bus.ownerName());
}
bool hybridFeedByte(uint8_t byte,uint32_t now){
    return feed_parser.feed(byte,now,[](uint32_t id,uint8_t op,const uint8_t* p,uint16_t n){feed_endpoint.receive(id,op,p,n);});
}
void hybridAbort(){feed_endpoint.transportFault();dual_servo_bus.emergencyOff();}
m4::dispense_bench::Observation feedSample(){
    const auto now=millis();uint16_t id=0;
    if(scale.calibration.valid()){
        uint8_t b[17]{1};uint64_t bits=0;
        std::memcpy(&bits,&scale.calibration.tare_counts,8);m4::calibration_record::put(b+1,bits,8);
        std::memcpy(&bits,&scale.calibration.grams_per_count,8);m4::calibration_record::put(b+9,bits,8);
        id=uart_v1::crc16(b,17);if(!id)id=1;
    }
    return {now,scale.grams.sampled_at_ms,scale.status.health==m4::Health::HEALTHY&&scale.grams.valid,
            scale.calibration.valid(),scale.grams.fresh,scale.grams.valid?scale.grams.value:0,id};
}
}
void setup(){
#ifdef MANUAL_STATION_HOST_TEST
    const uint32_t nonce=7654321;
#else
    const uint32_t random=esp_random();const uint32_t nonce=random?random:1;
#endif
    feed_endpoint.boot(nonce,false,false,0,millis());
    manualSetup();
}
void loop(){
    feed_endpoint.tick(feedSample(),feed_link::Closure{},false);
    manualLoop();
    feed_endpoint.tick(feedSample(),feed_link::Closure{},true);
    if(protocolSerial().overflowed())hybridAbort();
}
