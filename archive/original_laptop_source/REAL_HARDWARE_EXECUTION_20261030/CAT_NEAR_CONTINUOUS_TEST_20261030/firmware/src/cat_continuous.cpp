#include <Arduino.h>
#include <Preferences.h>
#include "board_config.h"
#include "current_hardware.h"
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/ledc_servo.h"
#include "m4/ultrasonic.h"
#include "continuous_hx_adapter.h"
#include "user_settings.h"
#include "test_wire.h"
using namespace forcat_continuous;
namespace {
class PersistentJournal:public Journal {
 public:
    bool initialized=false,pending=false,corrupt=false;uint32_t last=0;
    void load(){
        Preferences p;if(!p.begin("fc-cr-test",true))return;
        if(p.isKey("journal")){
            uint8_t b[12]{};
            if(p.getBytesLength("journal")!=12||p.getBytes("journal",b,12)!=12||b[0]!='C'||b[1]!='R'||b[2]!=1||b[3]>1||
                m4::calibration_record::get(b+10,2)!=uart_v1::crc16(b,10))corrupt=true;
            else {last=uint32_t(m4::calibration_record::get(b+4,4));pending=b[3];initialized=last<=0xffffffu;if(!initialized)corrupt=true;}
        }p.end();
    }
    bool write(bool value,uint32_t id)override{
        if(corrupt||id<last||id>0xffffffu)return false;
        uint8_t b[12]{'C','R',1,uint8_t(value)};m4::calibration_record::put(b+4,id,4);
        m4::calibration_record::put(b+10,uart_v1::crc16(b,10),2);
        Preferences p;if(!p.begin("fc-cr-test",false))return false;
        bool ok=p.putBytes("journal",b,12)==12;p.end();
        if(ok){initialized=true;pending=value;last=id;}return ok;
    }
};
m4::ArduinoPins pins;m4::Hx711 hx(pins);m4::Ultrasonic hc(pins);
m4::LedcServoOutput pwm;Driver motor(pwm);PersistentJournal journal;Controller control(motor,journal);
HxAdapter adapter;cat_test::Gate gate;cat_test::Receiver receiver;
uint32_t boot_id=0,last_hb=0,permit_at=0,last_ping=0,last_status=0;
bool configured=false,inspected=false,permit=false,hc_active=false,have_hb=false;
const char* calibration_source="NOT_CALIBRATED";
const char* calibration_load="NOT_ATTEMPTED";
char food='?';char rx[384]{};size_t rxn=0;bool discard=false;
bool quiet(){const auto s=control.state();return s==State::Disarmed||s==State::Fault||s==State::AwaitingOwner;}
void stop(){permit=false;control.stop(millis());}
void reply(uint32_t seq,bool ok,const char* detail){protocolSerial().printf("{\"type\":\"ack\",\"boot\":%lu,\"seq\":%lu,\"ok\":%s,\"detail\":\"%s\"}\n",(unsigned long)boot_id,(unsigned long)seq,ok?"true":"false",detail);}
void number(float v){if(std::isfinite(v))protocolSerial().printf("%.5f",double(v));else protocolSerial().print("null");}
void telemetry(const Sample& s){
    auto& out=protocolSerial();
    out.printf("{\"type\":\"status\",\"schema\":\"fc-cr-test-1\",\"boot\":%lu,\"ms\":%lu,\"seq\":%lu,\"state\":\"%s\",\"reason\":%u,\"configured\":%s,\"inspected\":%s,\"permit\":%s,\"pending\":%s,\"dose_id\":%lu,\"food\":\"%c\",\"cal_generation\":%lu,\"healthy\":%s,\"calibrated\":%s,\"sample_ms\":%lu,\"grams\":",
        (unsigned long)boot_id,(unsigned long)s.now_ms,(unsigned long)receiver.last(),name(control.state()),unsigned(control.reason()),configured?"true":"false",inspected?"true":"false",permit?"true":"false",journal.pending?"true":"false",(unsigned long)control.id(),food,(unsigned long)s.generation,s.healthy?"true":"false",s.calibrated?"true":"false",(unsigned long)s.sample_at_ms);
    number(s.healthy?s.grams:NAN);out.print(",\"baseline_g\":");number(control.baselineGrams());out.print(",\"dose_g\":");number(control.actualGrams());
    out.print(",\"near_cm\":");number(hc.raw.valid&&uint32_t(s.now_ms-hc.raw.sampled_at_ms)<=250?hc.raw.value:NAN);
    out.printf(",\"cat_fresh\":%s,\"close_trigger_g\":%.3f,\"calibration_source\":\"%s\",\"tare_counts\":",gate.catFresh(s.now_ms)?"true":"false",double(35-user_settings::settings().closing_lead_g),calibration_source);
    if(hx.calibration.valid())out.printf("%.17g,\"grams_per_count\":%.17g",hx.calibration.tare_counts,hx.calibration.grams_per_count);
    else out.print("null,\"grams_per_count\":null");
    out.printf(",\"hx_health\":\"%s\",\"hx_reason\":\"%s\",\"calibration_load\":\"%s\",\"raw_valid\":%s,\"raw\":",m4::name(hx.status.health),m4::name(hx.status.reason),calibration_load,hx.raw.valid?"true":"false");
    if(hx.raw.valid)out.printf("%ld",(long)hx.raw.value);else out.print("null");
    out.printf(",\"raw_ms\":%lu,\"median_raw_valid\":%s",(unsigned long)hx.raw.sampled_at_ms,hx.median_raw.valid?"true":"false");
    out.print(",\"physical_closed\":null,\"automatic\":false}\n");
}
void command(char* line,const Sample& s){
    // Read-only local monitor commands: no lease, ARM, calibration or motion.
    if(!std::strcmp(line,"hx")||!std::strcmp(line,"status")){telemetry(s);return;}
    if(!std::strcmp(line,"STOP")){stop();reply(0,true,"NEUTRAL_REQUESTED_CLOSURE_UNKNOWN");return;}
    cat_test::Packet p;if(!receiver.parse(line,boot_id,s.now_ms,p)){stop();reply(0,false,"BAD_FRAME_STOPPED");return;}
    bool ok=false;const char* detail="REJECTED";
    if(!std::strcmp(p.op,"HB")&&p.count==0){have_hb=true;last_hb=s.now_ms;control.heartbeat(s.now_ms);ok=true;}
    else if(!std::strcmp(p.op,"STOP")&&p.count==0){stop();ok=true;detail="NEUTRAL_REQUESTED_CLOSURE_UNKNOWN";}
    else if(!std::strcmp(p.op,"CAT")&&p.count==4){
        uint32_t seq,age,confidence,cat;
        ok=cat_test::number(p.args[0],seq)&&cat_test::number(p.args[1],age)&&cat_test::number(p.args[2],confidence)&&cat_test::number(p.args[3],cat)&&cat<=1&&
            gate.ai(s.now_ms,seq,age,s.now_ms-p.echo,confidence,cat);
    }else if(!std::strcmp(p.op,"INSPECT")&&p.count==1&&!std::strcmp(p.args[0],"CLOSED")&&quiet()){
        permit=false;configured=false;inspected=false;
        if(journal.write(false,journal.last)){
            control.boot(true,false,journal.last);gate.inspected();inspected=true;
            configured=control.configure(user_settings::settings());ok=true;
            detail=configured?"OWNER_INSPECTION_RECORDED":"INSPECTION_RECORDED_SETTINGS_INVALID";
        }else detail="JOURNAL_WRITE_FAILED";
    }else if(!std::strcmp(p.op,"ARM")&&p.count==1&&std::strlen(p.args[0])==1&&(p.args[0][0]=='A'||p.args[0][0]=='B')){
        ok=inspected&&configured&&hc_active&&!journal.pending&&!permit&&control.state()==State::Disarmed&&s.healthy&&s.calibrated&&have_hb&&s.now_ms-last_hb<1000;
        if(ok){food=p.args[0][0];permit=true;permit_at=s.now_ms;detail="PERMIT_30_SECONDS_NO_MOTION";}
    }
    reply(p.seq,ok,detail);
}
}
void setup(){
    protocolSerial().begin(115200);boot_id=esp_random();if(!boot_id)boot_id=1;
    journal.load();control.boot(journal.initialized,journal.pending,journal.last);
    hx.begin({{4,true},{5,true},500},millis());
    m4::CalibrationRecord record;m4::NvsCalibration nvs;
    const auto loaded=nvs.load(record);
    calibration_load=loaded==m4::CalibrationLoad::LOADED?"LOADED":loaded==m4::CalibrationLoad::INVALID?"INVALID":"MISSING";
    if(loaded==m4::CalibrationLoad::LOADED&&record.hx711.valid()){hx.applyCalibration(record.hx711);calibration_source="NVS_SENSORS_V2";}
    else if(user_settings::exact_calibration_import_reviewed&&std::strcmp(user_settings::calibration_provenance,"UNSET")&&std::strlen(user_settings::calibration_provenance)){
        m4::ScaleCalibration c;c.tared=c.calibrated=true;c.tare_counts=user_settings::tare_counts;c.grams_per_count=user_settings::grams_per_count;
        if(c.valid()){hx.applyCalibration(c);calibration_source="EXACT_REVIEWED_IMPORT";}
    }
    if(user_settings::hc_sr04_wiring_reviewed)hc_active=hc.begin({{12,true},{13,true},user_settings::hc_min_cm,user_settings::hc_max_cm,30000,0.0343f});
}
void loop(){
    const uint32_t now=millis();hc.poll(micros(),now);
    if(hc.raw.fresh)gate.near(now,hc.raw.valid,hc.raw.value);
    // Keep tight acoustic polling; no Serial formatting/HX pulse train during ECHO.
    if(!hc.busy())hx.poll(now);
    const Sample s=adapter.read(hx,now);control.tick(s,Position{});
    if(permit&&(uint32_t(now-permit_at)>=30000||!have_hb||uint32_t(now-last_hb)>=1500))permit=false;
    if(!hc.busy()){
        unsigned budget=128;
        while(budget--&&protocolSerial().available()){
            const int value=protocolSerial().read();if(value<0)break;const char c=char(value);
            if(c=='\r')continue;
            if(c=='\n'){if(!discard&&rxn){rx[rxn]=0;command(rx,s);}rxn=0;discard=false;}
            else if(!discard){if(c<32||c>126||rxn+1>=sizeof(rx)){discard=true;rxn=0;stop();}else rx[rxn++]=c;}
        }
        if(permit&&gate.ready(now)&&s.fresh&&s.healthy){
            permit=false;gate.consume();
            if(control.arm(s,Position{},Mode::Supervised,true)==Reason::None){
                control.start(journal.last+1,s);inspected=false;
            }
        }
        if(now-last_status>=250){last_status=now;telemetry(s);}
        protocolSerial().drain();if(protocolSerial().overflowed())stop();
        if(hc_active&&gate.catFresh(now)&&now-last_ping>=70){last_ping=now;hc.trigger(micros());}
    }
}
