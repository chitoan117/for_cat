#include <Arduino.h>
#include "board_config.h"
#if defined(DOG_BUZZER_DIAGNOSTIC) && DOG_BUZZER_DIAGNOSTIC
#include "serial_port.h"
#include "m4/arduino_io.h"
#include "m4/approach_dog_warning.h"
#include <cstring>
static_assert(ACTUATOR_OUTPUTS_ENABLED==0,"Buzzer-only diagnostic has no actuator permission");
namespace {
m4::ArduinoPins io;m4::approach_dog::Buzzer buzzer(io);
char line[40]{};unsigned used=0;bool discard=false;
}
void setup(){
  buzzer.begin();protocolSerial().begin(115200);
  protocolSerial().println("MH-FMD GPIO2 ACTIVE_LOW3V3 OFF; servo/pump UNTOUCHED. Diagnostic only: test CONFIRM (2x200ms,60s cooldown)");
}
void loop(){
  buzzer.tick(millis());
  for(unsigned i=0;i<32 && protocolSerial().available();++i){
    const char c=static_cast<char>(protocolSerial().read());
    if(c=='\r'||c=='\n'){
      if(!discard && used){line[used]=0;protocolSerial().println(std::strcmp(line,"test CONFIRM")==0 && buzzer.start(millis())?"ACCEPTED_DIAGNOSTIC_NOT_DOG_DETECTION":"REJECTED_BUSY_COOLDOWN_OR_COMMAND");}
      used=0;discard=false;
    }else if(c>=32 && c<=126 && !discard){if(used<sizeof(line)-1)line[used++]=c;else{used=0;discard=true;}}
    else{used=0;discard=true;}
  }
  yield();
}
#endif
