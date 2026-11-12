#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include "m4/diagnostic_config.h"
#include "m4/arduino_io.h"
#include "m4/hx711.h"
#include "m4/ledc_servo.h"
#include "m4/approach_dog_warning.h"
#include "serial_port.h"
#include "feed_link.h"
#include "dog_warning_protocol.h"

#ifndef FORCAT_FEED_PHYSICAL_ENABLE
#define FORCAT_FEED_PHYSICAL_ENABLE 0
#endif
#ifndef FORCAT_FEED_BUZZER_ENABLE
#define FORCAT_FEED_BUZZER_ENABLE 0
#endif
#if !defined(FORCAT_FEED_LINK) || FORCAT_FEED_LINK!=1 || ACTUATOR_OUTPUTS_ENABLED!=0 || \
    !defined(FORR_REAL_S3_NO_PSRAM) || FORR_NATIVE_USB || ARDUINO_USB_CDC_ON_BOOT || SERVO_BENCH_MODE || PUMP_BENCH_MODE || DISPENSE_BENCH_MODE
#error "Dedicated S3 UART0 protocol candidate only; never mix normal/manual entry points"
#endif
static_assert(current_hardware::SERVO_SIGNAL==6 && current_hardware::HX711_DOUT==4 && current_hardware::HX711_SCK==5,"Frozen GPIO contract");
namespace {
class Journal:public m4::dispense_bench::Journal {
 public:
    bool load(bool& pending,uint32_t& id){
        pending=false;id=0;Preferences p;if(!p.begin("fc-feed-v1",true))return false;
        uint8_t b[7]{};const bool read=p.getBytesLength("txn-v1")==7 && p.getBytes("txn-v1",b,7)==7;p.end();
        if(!read || b[0]!=1 || b[1]>1 || uart_v1::crc16(b,5)!=feed_link::get16(b+5))return false;
        pending=b[1]!=0;id=uint32_t(b[2])|uint32_t(b[3])<<8|uint32_t(b[4])<<16;return true;
    }
    bool write(bool pending,uint32_t id)override{
#if FORCAT_FEED_PHYSICAL_ENABLE
        if(id>0xffffffu)return false;
        uint8_t b[7]{1,static_cast<uint8_t>(pending),static_cast<uint8_t>(id),static_cast<uint8_t>(id>>8),static_cast<uint8_t>(id>>16),0,0};
        feed_link::put16(b+5,uart_v1::crc16(b,5));Preferences p;if(!p.begin("fc-feed-v1",false))return false;
        const bool saved=p.putBytes("txn-v1",b,7)==7;p.end();bool got_pending=false;uint32_t got_id=0;
        return saved && load(got_pending,got_id) && got_pending==pending && got_id==id;
#else
        (void)pending;(void)id;return false; // released inert candidate cannot write this NVS journal
#endif
    }
};
class Sink:public feed_link::Sink {
 public:
    void emit(uint32_t id,uint8_t op,const uint8_t* p,uint16_t n)override{
        uint8_t bytes[uart_v1::MAX_FRAME]{};size_t size=0;
        if(uart_v1::encode(id,op,p,n,bytes,sizeof(bytes),size))protocolSerial().write(bytes,size);
    }
};
class Warning:public feed_link::Warning {
    m4::ArduinoPins io_;m4::approach_dog::Buzzer buzzer_{io_};bool initialized_=false;unsigned starts_=0;
 public:
    bool pulse(uint32_t now)override{
#if FORCAT_FEED_PHYSICAL_ENABLE && FORCAT_FEED_BUZZER_ENABLE
        if(starts_>=3)return false;
        if(!initialized_){buzzer_.begin();initialized_=true;}
        if(!buzzer_.start(now))return false;++starts_;return true;
#else
        (void)now;return false;
#endif
    }
    void tick(uint32_t now){if(initialized_)buzzer_.tick(now);}
};
m4::ArduinoPins io;
m4::Hx711 scale(io);
m4::NvsCalibration calibration_store;
m4::CalibrationRecord calibration;
m4::LedcServoOutput output;
Journal journal;Sink sink;Warning warning;
feed_link::Endpoint endpoint(output,journal,sink,warning,FORCAT_FEED_PHYSICAL_ENABLE!=0);
dog_wire::Parser parser;
uint16_t calibrationId(){
    if(!scale.calibration.valid())return 0;
    uint8_t b[17]{1};uint64_t bits=0;
    std::memcpy(&bits,&scale.calibration.tare_counts,8);m4::calibration_record::put(b+1,bits,8);
    std::memcpy(&bits,&scale.calibration.grams_per_count,8);m4::calibration_record::put(b+9,bits,8);
    const auto crc=uart_v1::crc16(b,17);return crc?crc:1;
}
}
void setup(){
    protocolSerial().begin(115200);
    bool pending=false;uint32_t last=0;const bool initialized=journal.load(pending,last);
    const auto nonce=esp_random();endpoint.boot(nonce?nonce:1,initialized,pending,last,millis());
    calibration_store.load(calibration);scale.applyCalibration(calibration.hx711);
    scale.begin({{4,true},{5,true},500},millis());
    protocolSerial().println("FORCAT_FEED_LINK_V1 CAPABILITIES REQUIRED; DEFAULT NO PHYSICAL ENABLE; PUMP7 UNTOUCHED; NO CALIBRATION WRITE");
}
void loop(){
    const auto now=millis();scale.poll(now);
    m4::dispense_bench::Observation sample{now,scale.grams.sampled_at_ms,
        scale.status.health==m4::Health::HEALTHY && scale.grams.valid,scale.calibration.valid(),scale.grams.fresh,
        scale.grams.valid?scale.grams.value:0,calibrationId()};
    // No closure sensor/qualification is invented. Real automatic ARM remains
    // blocked until an actual qualified closure provider is integrated/reviewed.
    const feed_link::Closure closure{};
    endpoint.tick(sample,closure,false);
    for(unsigned n=0;n<32 && protocolSerial().available();++n){
        const auto byte=static_cast<uint8_t>(protocolSerial().read());
        parser.feed(byte,now,[](uint32_t id,uint8_t op,const uint8_t* p,uint16_t count){endpoint.receive(id,op,p,count);});
    }
    endpoint.tick(sample,closure,true);warning.tick(now);
    if(protocolSerial().overflowed())endpoint.transportFault();
    protocolSerial().drain();yield();
}
