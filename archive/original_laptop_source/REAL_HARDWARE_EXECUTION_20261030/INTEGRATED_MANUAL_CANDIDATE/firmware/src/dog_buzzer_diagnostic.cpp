#include <Arduino.h>
#include "board_config.h"
#include "physical_kit_identity.h"
#if defined(DOG_BUZZER_DIAGNOSTIC) && DOG_BUZZER_DIAGNOSTIC
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/approach_dog_warning.h"
#include <cstring>
static_assert(ACTUATOR_OUTPUTS_ENABLED==0,"Buzzer-only diagnostic has no actuator permission");
namespace {
m4::ArduinoPins io;m4::approach_dog::Buzzer buzzer(io);
char line[40]{};unsigned used=0;bool discard=false;
bool driver_confirmed=false;unsigned tests_started=0;
void kitCommand(const char* text){
  if(std::strcmp(text,"status")==0){
    physicalKitBanner(protocolSerial(),"diag_dog_buzzer");
    protocolSerial().printf("BUZZER_STATUS profile=diag_dog_buzzer polarity=ACTIVE_LOW_3V3 driver_ack=%u tests=%u/3 phase=%u physical_pass=false\r\n",driver_confirmed?1u:0u,tests_started,buzzer.phase());return;
  }
  if(std::strcmp(text,"buzzer-driver ACTIVE_LOW CONFIRM")==0){driver_confirmed=true;protocolSerial().println("DRIVER_ACK_ONLY_NOT_ELECTRICAL_PROOF_NO_SOUND");return;}
  if(std::strcmp(text,"stop")==0){buzzer.begin();protocolSerial().println("BUZZER_STOP_HIGH_COMMANDED_NOT_ACOUSTIC_PROOF");return;}
  if(std::strcmp(text,"test CONFIRM")==0 && driver_confirmed && tests_started<3 && buzzer.start(millis())){
    ++tests_started;protocolSerial().println("ACCEPTED_DIAGNOSTIC_NOT_DOG_DETECTION");return;
  }
  protocolSerial().println("REJECTED_DRIVER_ACK_BUDGET_COOLDOWN_OR_COMMAND");
}
}
void setup(){
   buzzer.begin();protocolSerial().begin(115200);
   driver_confirmed=false;tests_started=0;
   physicalKitBanner(protocolSerial(),"diag_dog_buzzer");
   protocolSerial().println("GPIO2 ACTIVE_LOW3V3 HIGH_OFF. Require measured module logic then buzzer-driver ACTIVE_LOW CONFIRM; test CONFIRM; status; stop. 2x200ms/gap200ms,60s cooldown,max3tests/boot. NO AI/FEED/PUMP.");
}
void loop(){
  buzzer.tick(millis());
  for(unsigned i=0;i<32 && protocolSerial().available();++i){
    const char c=static_cast<char>(protocolSerial().read());
    if(c=='\r'||c=='\n'){
      if(!discard && used){line[used]=0;kitCommand(line);}
      used=0;discard=false;
    }else if(c>=32 && c<=126 && !discard){if(used<sizeof(line)-1)line[used++]=c;else{used=0;discard=true;}}
    else{used=0;discard=true;}
  }
  yield();
}
#endif
