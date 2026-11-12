#include "sim_support.h"
using namespace offline_demo;
int main() {
 try {
  Log log(1793203200000ULL);
  unsigned checks=0;
  auto check=[&](bool ok,const char* why){++checks;require(ok,why);};
  {
    Clock c("MCU_RESTART");log.context(c,"DOG_RESTART_NEAR");Harness h(c,log);
    h.prepare();h.arrival("DOG");h.advance(1000);
    check(h.warnings_received==1 && h.buzzer.completed()==1,"first warning missing");
    // Same reset/HELLO boundary used by bridge on changed MCU boot.
    h.boot_nonce=789;h.link_token=987;h.receiver.begin(h.boot_nonce);h.fusion.reset();
    uint8_t hello[9]{1};dog_wire::put(hello+1,h.boot_nonce);dog_wire::put(hello+5,h.link_token);
    h.send(dog_wire::HELLO,hello,9,false,0);h.deliver();
    h.distance=19;h.advance(3000);
    check(h.warnings_received==1 && h.auto_requests==0,"restart near caused action");
    uint8_t old[21]{1};dog_wire::put(old+1,123);dog_wire::put(old+5,456);
    check(h.receiver.receive(500,dog_wire::WARNING,old,21,c.now)==m4::approach_dog::OLD_SESSION,"old boot replay accepted");
    h.jump(60000);h.arrival("DOG");h.advance(1000);
    check(h.warnings_received==2 && h.buzzer.completed()==2,"release/rearm recovery failed");
    check(h.servo.opens==0,"DOG opened fake servo");
  }
  {
    Clock c("AI_RESTART");log.context(c,"AI_STALE_RECOVERY");Harness h(c,log);
    h.prepare();h.ai_fresh=false;h.arrival("CAT");
    check(h.auto_requests==0 && h.servo.opens==0,"stale AI fed");
    // Detector disappearance resets temporal evidence through fresh=false.
    h.scene("NONE");h.advance(2000);h.ai_seq=0;
    h.ai_fresh=true;h.scene("CAT");h.advance(2000);
    check(h.auto_requests==0,"expired old approach replayed on AI restart");
    h.arrival("CAT");check(h.auto_requests==1,"fresh CAT encounter failed recovery");
    h.dispense();check(h.feed_success && h.successes==1,"CAT fake dispense failed");
    h.advance(1500);check(h.auto_requests==1 && h.successes==1,"duplicate AUTO_CAT");
    h.ai_fresh=false;h.advance(2000);h.ai_fresh=true;h.ai_seq=0;h.advance(2000);
    check(h.auto_requests==1,"AI restart repeated consumed event");
  }
  Clock summary("SUMMARY");log.context(summary,"RESTART_FUSION");
  log.event("RESTART_FUSION_RESULT",{{"status",quote("PASS")},{"checks",integer(checks)},
    {"physical_pass","false"},{"actuators",quote("FAKE_ONLY")}});
 } catch(const std::exception& e) {std::cerr<<"RESTART_FUSION_FAIL "<<e.what()<<'\n';return 1;}
}
