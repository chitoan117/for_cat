// FOR_CAT standalone JSN pulse/ECHO test. No servo, pump, buzzer or NVS access.
// JSN1 = US3: TRIG14 / ECHO15. JSN2 = US4: TRIG18 / ECHO10.
// ESP32S3 Dev Module, USB CDC On Boot Disabled, external UART0 115200.
#include <Arduino.h>
#include <cmath>
#include <cstdio>
#include <cstring>

#if !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "Select ESP32S3 Dev Module"
#endif
#if ARDUINO_USB_CDC_ON_BOOT
#error "Disable USB CDC On Boot: this sketch uses Serial0"
#endif

class JsnTest {
    struct Channel {
        const char* name;
        int trig,echo;
        bool attempted=false;
        uint32_t sample_ms=0,pulse_us=0;
        const char* result="NOT_SAMPLED";
        float cm=0;
    };
    enum class Phase {Idle,Low,High,Rise,Fall};
    Channel ch_[2]{{"JSN1_US3",14,15},{"JSN2_US4",18,10}};
    Phase phase_=Phase::Idle;
    unsigned selected_=0,next_=0,mask_=0;
    uint32_t phase_at_=0,began_=0,rise_at_=0,last_ping_=0;
    static constexpr uint32_t TIMEOUT_US=45000;
    static constexpr uint32_t PING_INTERVAL_MS=150;
    // Reference test envelope only; verify the exact JSN model/mode datasheet.
    static constexpr float TEST_MIN_CM=25.0f,TEST_MAX_CM=600.0f;
    static constexpr float SOUND_CM_PER_US=0.0343f;
    char line_[64]{};size_t line_n_=0;bool discard_=false;
    uint8_t tx_[4096]{};size_t head_=0,count_=0;bool overflow_=false;

    void emit(const char* s){
        const size_t n=strlen(s);
        if(n>sizeof(tx_)-count_){overflow_=true;mask_=0;return;}
        for(size_t i=0;i<n;++i)tx_[(head_+count_++)%sizeof(tx_)]=uint8_t(s[i]);
    }
    void drain(){
        const int room=Serial0.availableForWrite();
        size_t n=room>0?size_t(room):0;
        if(n>64)n=64;if(n>count_)n=count_;if(n>sizeof(tx_)-head_)n=sizeof(tx_)-head_;
        if(n){size_t done=Serial0.write(tx_+head_,n);head_=(head_+done)%sizeof(tx_);count_-=done;}
    }
    void report(unsigned i){
        const auto& c=ch_[i];char b[384];
        const bool has_distance=!strcmp(c.result,"PULSE_OK");
        const char* band=has_distance?(c.cm<TEST_MIN_CM?"BELOW_TEST_MIN":c.cm>TEST_MAX_CM?"ABOVE_TEST_MAX":"IN_TEST_RANGE"):"UNKNOWN";
        char distance[32];
        if(has_distance)snprintf(distance,sizeof(distance),"%.2f",double(c.cm));else strcpy(distance,"null");
        snprintf(b,sizeof(b),"{\"sensor\":\"%s\",\"trig\":%d,\"echo\":%d,\"sampled\":%s,\"sample_ms\":%lu,\"result\":\"%s\",\"pulse_us\":%lu,\"distance_cm\":%s,\"test_band\":\"%s\",\"echo_now\":%d}\n",
            c.name,c.trig,c.echo,c.attempted?"true":"false",(unsigned long)c.sample_ms,c.result,(unsigned long)c.pulse_us,distance,band,digitalRead(c.echo)==HIGH?1:0);
        emit(b);
    }
    void finish(const char* result,uint32_t width=0){
        auto& c=ch_[selected_];digitalWrite(c.trig,LOW);
        c.attempted=true;c.sample_ms=millis();c.pulse_us=width;c.result=result;
        c.cm=float(width)*SOUND_CM_PER_US/2.0f;
        phase_=Phase::Idle;report(selected_);
    }
    void beginPing(unsigned i){
        selected_=i;last_ping_=millis();
        if(digitalRead(ch_[i].echo)==HIGH){finish("ECHO_HIGH_BEFORE_TRIGGER");return;}
        digitalWrite(ch_[i].trig,LOW);began_=phase_at_=micros();phase_=Phase::Low;
    }
    void poll(){
        if(phase_==Phase::Idle)return;
        const uint32_t now=micros();
        if(uint32_t(now-began_)>=TIMEOUT_US){
            finish(phase_==Phase::Fall?"TIMEOUT_WAIT_FALL":"TIMEOUT_WAIT_RISE_OR_TRIGGER");return;
        }
        switch(phase_){
            case Phase::Low:
                if(uint32_t(now-phase_at_)>=2){digitalWrite(ch_[selected_].trig,HIGH);phase_at_=now;phase_=Phase::High;}
                break;
            case Phase::High:
                if(uint32_t(now-phase_at_)>=10){digitalWrite(ch_[selected_].trig,LOW);phase_=Phase::Rise;}
                break;
            case Phase::Rise:
                if(digitalRead(ch_[selected_].echo)==HIGH){rise_at_=now;phase_=Phase::Fall;}
                break;
            case Phase::Fall:
                if(digitalRead(ch_[selected_].echo)==LOW){
                    const uint32_t width=uint32_t(now-rise_at_);
                    finish(width?"PULSE_OK":"ZERO_WIDTH",width);
                }
                break;
            default:break;
        }
    }
    void help(){
        emit("FOR_CAT JSN TEST: jsn1/us3 | jsn2/us4 | both | status | stop | help\n");
        emit("JSN1=TRIG14/ECHO15; JSN2=TRIG18/ECHO10. Boot STOPPED. UART0 115200 Newline.\n");
        emit("Pulse/ECHO mode only. ECHO at ESP32 input must be <=3.3V. PULSE_OK is not calibrated accuracy.\n");
    }
    void command(){
        line_[line_n_]=0;
        if(!strcmp(line_,"jsn1")||!strcmp(line_,"us3")){mask_=1;next_=0;emit("STREAM JSN1_US3\n");}
        else if(!strcmp(line_,"jsn2")||!strcmp(line_,"us4")){mask_=2;next_=1;emit("STREAM JSN2_US4\n");}
        else if(!strcmp(line_,"both")){mask_=3;next_=0;emit("STREAM BOTH sequentially, 150ms between trigger starts\n");}
        else if(!strcmp(line_,"stop")||!strcmp(line_,"STOP")){mask_=0;emit("STOPPED\n");}
        else if(!strcmp(line_,"status")){report(0);report(1);}
        else if(!strcmp(line_,"help")){help();}
        else emit("UNKNOWN COMMAND: type help\n");
    }
 public:
    void begin(){
        Serial0.begin(115200);
        for(auto& c:ch_){pinMode(c.trig,OUTPUT);digitalWrite(c.trig,LOW);pinMode(c.echo,INPUT);}
        help();
    }
    void tick(){
        poll();
        // Tight polling during ECHO capture. Commands wait at most one timeout.
        if(phase_!=Phase::Idle)return;
        unsigned budget=64;
        while(budget--&&Serial0.available()){
            int b=Serial0.read();if(b<0)break;char c=char(b);
            if(c=='\r')continue;
            if(c=='\n'){
                if(!discard_&&line_n_)command();
                line_n_=0;discard_=false;
            }else if(!discard_){
                if(c<32||c>126||line_n_+1>=sizeof(line_)){
                    mask_=0;line_n_=0;discard_=true;emit("RX_ERROR_STREAM_STOPPED\n");
                }else line_[line_n_++]=c;
            }
        }
        if(overflow_){mask_=0;if(!count_){overflow_=false;emit("TX_OVERFLOW_STREAM_STOPPED\n");}}
        drain();
        if(mask_&&uint32_t(millis()-last_ping_)>=PING_INTERVAL_MS){
            unsigned i=next_;
            if(!(mask_&(1u<<i)))i=1-i;
            next_=1-i;beginPing(i);
        }
    }
};

JsnTest jsn;
void setup(){jsn.begin();}
void loop(){jsn.tick();}
