#include "sim_support.h"
using namespace offline_demo;
int main() {
 try {
  Log log(1793203200000ULL);unsigned checks=0;
  auto check=[&](bool value,const char* reason){++checks;require(value,reason);};
  {
    Clock c("INOX_DISLIKE");log.context(c,"D_J_GROSS95_FOOD35_CONSUMED5");Harness h(c,log);
    h.mass=h.empty_container_gross=95;h.enforce_empty_container=true;
    h.prepare();h.arrival("CAT");h.dispense();
    check(h.successes==1 && h.last_actual==35 && h.mass==130,"gross/delta failure");
    check(h.beginMeal("FOOD_B"),"meal did not start");
    const auto start=c.now;const auto opens=h.servo.opens;
    while(c.now-start<60000){h.mass=c.now-start<20000?130:125;h.step();}
    check(h.preference_result.valid && h.preference_result.consumed==5 && h.preference_result.classification=="DISLIKE","consumption5 must DISLIKE");
    check(h.servo.opens==opens && h.successes==1,"weight loss caused top-up");
    h.clearBowl();check(h.mass==95,"bowl removed on clear");
    log.event("OVERNIGHT_CASE",{{"status",quote("PASS")},{"case",quote("INOX_DISLIKE_NO_TOPUP")}});
  }
  {
    Clock c("INOX_INVALID");log.context(c,"E_INVALID_HX_BLOCKS");Harness h(c,log);
    h.mass=h.empty_container_gross=95;h.enforce_empty_container=true;h.sensor_fault=SensorFault::RAW_INVALID;
    h.prepare();h.arrival("CAT");
    check(h.auto_requests==1 && h.servo.opens==0 && !h.feeding,"invalid scale fed");
    check(!h.weightValid(),"invalid scale fabricated weight");
    log.event("OVERNIGHT_CASE",{{"status",quote("PASS")},{"case",quote("INVALID_HX_NO_FEED")}});
  }
  {
    Clock c("INOX_AI_LOSS");log.context(c,"F_AI_LOSS_DURING_FAKE_FEED");Harness h(c,log);
    h.mass=h.empty_container_gross=95;h.enforce_empty_container=true;h.prepare();h.arrival("CAT");
    h.dispense("AI_STALE");
    check(h.successes==0 && !h.feed_success && h.servo.angle==90 && h.errors==1,"AI loss not fail-closed");
    check(h.last_error=="AI_NOT_FRESH_CAT","wrong stale failure");
    log.event("OVERNIGHT_CASE",{{"status",quote("PASS")},{"case",quote("AI_STALE_FAIL_CLOSED")}});
  }
  {
    Clock c("INOX_UART");log.context(c,"B_G_DOG_CRC_DUPLICATE");Harness h(c,log);
    h.mass=h.empty_container_gross=95;h.enforce_empty_container=true;h.prepare();
    h.crc_corrupt=true;h.arrival("DOG");h.advance(1000);
    check(h.warnings_received==0 && h.buzzer_io.lows==0 && h.servo.opens==0,"bad CRC caused output");
    h.crc_corrupt=false;h.warning();h.deliver();h.advance(1000);
    check(h.warnings_received==1 && h.buzzer_io.lows==2 && h.buzzer.completed()==1,"good warning not2beeps");
    h.warning();h.deliver();h.advance(1000);
    check(h.warnings_received==1 && h.buzzer_io.lows==2 && h.servo.opens==0,"duplicate event reexecuted");
    log.event("OVERNIGHT_CASE",{{"status",quote("PASS")},{"case",quote("CRC_DUPLICATE_NO_REEXECUTION")}});
  }
  Clock summary("SUMMARY");log.context(summary,"OVERNIGHT_FOCUSED_E2E");
  log.event("OVERNIGHT_E2E_RESULT",{{"status",quote("PASS")},{"checks",integer(checks)},{"new_scenarios","4"},{"physical_pass","false"}});
 } catch(const std::exception& e) {std::cerr<<"OVERNIGHT_E2E_FAIL "<<e.what()<<'\n';return 1;}
}
