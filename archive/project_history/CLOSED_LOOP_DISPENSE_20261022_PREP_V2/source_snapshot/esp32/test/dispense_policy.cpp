// Portable policy fault matrix. No Arduino, GPIO, camera, food or real sensor.
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "m4/dispense_bench.h"

namespace db=m4::dispense_bench;
unsigned assertions=0,named=0;
void check(bool pass,const char* text) { ++assertions; if (!pass) throw std::runtime_error(text); }
struct FakeOutput : m4::servo_bench::Output {
  bool attached=false,fail_write=false,fail_off=false,fail_start=false;
  unsigned opens=0,closes=0,offs=0;
  bool start(uint16_t us) override {
    if (fail_start||attached||us!=1500) return false;
    attached=true;++closes;return true;
  }
  bool write(uint16_t us) override {
    if (!attached||fail_write) return false;
    if (us==1560) ++opens;
    else if (us==1500) ++closes;
    else return false;
    return true;
  }
  bool off() override { ++offs;if (fail_off) return false;attached=false;return true; }
};
struct FakeJournal : db::Journal {
  bool pending=false,fail=false;uint32_t id=0;unsigned writes=0;
  bool write(bool next,uint32_t number) override {
    ++writes;if(fail)return false;
    pending=next;id=number;return true;
  }
};
struct Fixture {
  FakeOutput out;FakeJournal store;db::Controller controller{out,store};
  db::Observation obs{0,0,true,true,true,0,123};
  db::Settings cfg{1400,1600,1500,1560,100,40,500,5,2.0f,0.2f,0.2f,5.0f,8.0f};
  Fixture() { controller.boot(true,false,0); }
  void ready() {
    check(controller.configure(cfg),"bench settings not configured");
    check(controller.arm(obs)==db::Reason::NONE,"manual arm failed");
  }
  void start(float target=3,uint32_t id=1) {
    ready();check(controller.start(id,target,obs)==db::Reason::NONE,"manual test start failed");
    check(store.pending && store.id==id,"write-ahead NVS protection not set");
  }
  db::Event step(uint32_t advance=100) {
    obs.now_ms+=advance;obs.sample_at_ms=obs.now_ms;obs.fresh=true;
    const db::Event e=controller.tick(obs);
    if (e==db::Event::NONE && controller.pulsePending()) return controller.launchPulse(obs);
    return e;
  }
  db::Event waitFor(db::Event expected,unsigned budget=500) {
    for(unsigned i=0;i<budget;++i) { auto event=step();if(event==expected)return event; }
    throw std::runtime_error("event missing within bounded host replay");
  }
};
void case_run(const char* name,void (*func)()) { std::cerr<<"RUN "<<name<<'\n';func();++named;std::cout<<"PASS "<<name<<std::endl; }
void test_target_already_reached() {
  Fixture f; f.start(1);
  f.waitFor(db::Event::BASELINE);f.waitFor(db::Event::FINE);
  f.waitFor(db::Event::CLOSE);f.obs.grams=1.1f;
  f.waitFor(db::Event::COMPLETE);
  check(f.controller.pulses()==1,"target reached but extra pulse launched");
  check(!f.out.attached && !f.store.pending,"completion left PWM or NVS lock");
}
void test_multipulse_coarse_fine() {
  Fixture f;f.start(3);
  f.waitFor(db::Event::BASELINE);
  check(f.waitFor(db::Event::COARSE)==db::Event::COARSE,"first pulse not coarse");
  f.waitFor(db::Event::CLOSE);f.obs.grams=1.5f;
  f.waitFor(db::Event::MEASUREMENT);f.waitFor(db::Event::FINE);
  f.waitFor(db::Event::CLOSE);f.obs.grams=2.6f;
  f.waitFor(db::Event::MEASUREMENT);f.waitFor(db::Event::FINE);
  f.waitFor(db::Event::CLOSE);f.obs.grams=3.1f;
  f.waitFor(db::Event::COMPLETE);
  check(f.controller.pulses()==3 && f.out.opens==3 && f.controller.dispensed()>3.0f,
        "multipulse/overshoot not measured from stable baseline");
  check(!f.out.attached && f.out.closes>=3,"servo not closed after every pulse");
}
void test_faults() {
  Fixture f; check(f.controller.configure(f.cfg),"fixture config");f.obs.calibrated=false;
  check(f.controller.arm(f.obs)==db::Reason::HX711_NOT_CALIBRATED,"uncalibrated accepted");
  f.obs.calibrated=true;f.obs.healthy=false;
  check(f.controller.arm(f.obs)==db::Reason::HX711_NOT_READY,"notready accepted");
  f.obs.healthy=true;f.obs.now_ms=2000;f.obs.sample_at_ms=0;
  check(f.controller.arm(f.obs)==db::Reason::HX711_NOT_READY,"stale sample accepted");
  f.obs.sample_at_ms=f.obs.now_ms;
  check(f.controller.start(1,3,f.obs)==db::Reason::NOT_ARMED,"disarmed request accepted");
  check(f.controller.arm(f.obs)==db::Reason::NONE,"fixture arm failed");
  check(f.controller.start(1,0,f.obs)==db::Reason::INVALID_TARGET,"zero target accepted");
  check(f.controller.start(1,99,f.obs)==db::Reason::INVALID_TARGET,"out-of-range target accepted");
  check(f.out.opens==0 && !f.store.pending,"invalid commands moved or persisted");
}
void test_baseline_unstable() {
  Fixture f;f.start();
  for(unsigned n=0;n<110;++n) {
    f.obs.grams=(n%2)?1.0f:0.0f;
    f.step();
    if (f.controller.state()==db::State::FAULT) break;
  }
  check(f.controller.reason()==db::Reason::BASELINE_UNSTABLE && f.out.opens==0,
        "unstable baseline opened servo");
  check(!f.out.attached && f.store.pending,"unstable baseline did not fail closed/lock");
}
void test_scale_unstable() {
  Fixture f;f.start();f.waitFor(db::Event::BASELINE);f.waitFor(db::Event::COARSE);
  f.waitFor(db::Event::CLOSE);
  for(unsigned n=0;n<150;++n) {
    f.obs.grams=(n%2)?2.0f:0.0f;
    f.step();
    if(f.controller.state()==db::State::FAULT) break;
  }
  check(f.controller.reason()==db::Reason::SCALE_UNSTABLE && !f.out.attached && f.store.pending,
        "unstable postpulse reading enabled more pulses");
}
void test_limits() {
  Fixture f;f.cfg.max_pulses=1;f.start(3);
  f.waitFor(db::Event::BASELINE);f.waitFor(db::Event::COARSE);
  f.waitFor(db::Event::CLOSE);f.obs.grams=0.5f;
  f.waitFor(db::Event::FAULT);
  check(f.controller.reason()==db::Reason::MAX_PULSES_REACHED && !f.out.attached,
        "pulse cap did not close");
  Fixture huge;huge.start(3);huge.waitFor(db::Event::BASELINE);huge.waitFor(db::Event::COARSE);
  huge.waitFor(db::Event::CLOSE);huge.obs.grams=10.0f;
  huge.waitFor(db::Event::FAULT);
  check(huge.controller.reason()==db::Reason::MAX_GRAMS_EXCEEDED && !huge.out.attached,
        "grams ceiling failed");
  Fixture timed;timed.start();timed.obs.now_ms+=60000;timed.obs.sample_at_ms=timed.obs.now_ms;
  check(timed.controller.tick(timed.obs)==db::Event::FAULT &&
        timed.controller.reason()==db::Reason::MAX_TIME_REACHED,"time bound absent");
  timed.step(400);check(!timed.out.attached,"max-time fault left PWM attached");
}
void test_abort_duplicate_persistence() {
  Fixture f;f.start();
  check(f.controller.start(1,3,f.obs)==db::Reason::DUPLICATE,"duplicate command retriggered");
  check(f.controller.abort(f.obs.now_ms)==db::Reason::ABORTED,"abort not recognized");
  for (unsigned n=0;n<10;++n) {
    check(f.controller.abort(f.obs.now_ms+n)==db::Reason::BUSY,"repeat abort extended fault timer");
    f.controller.disarm(f.obs.now_ms+n);
  }
  f.step(400);
  check(!f.out.attached && f.store.pending && f.controller.locked(),"abort lost pending inspection lock");
  f.controller.boot(true,f.store.pending,f.store.id);check(f.controller.locked(),"reboot resumed unsafe session");
  check(f.controller.arm(f.obs)==db::Reason::INSPECTION_REQUIRED,"reboot pending allowed PWM");
  check(f.controller.inspect(f.obs.now_ms),"explicit inspection could not clear lock");
  f.ready();check(f.controller.start(1,3,f.obs)==db::Reason::DUPLICATE,"reboot replay accepted");
}
void test_sensor_fault_and_pwm() {
  Fixture f;f.start();f.waitFor(db::Event::BASELINE);f.waitFor(db::Event::COARSE);
  f.obs.healthy=false;f.step();f.step(400);
  check(f.controller.reason()==db::Reason::HX711_NOT_READY && !f.out.attached && f.store.pending,
        "HX fault left servo open");
  Fixture pwm;pwm.start();pwm.waitFor(db::Event::BASELINE);
  pwm.out.fail_write=true; pwm.waitFor(db::Event::FAULT);
  check(pwm.controller.reason()==db::Reason::SERVO_FAULT && !pwm.out.attached,
        "PWM write fault not surfaced");
  Fixture nv;nv.start();nv.waitFor(db::Event::BASELINE);nv.waitFor(db::Event::COARSE);
  nv.waitFor(db::Event::CLOSE);nv.obs.grams=3;nv.store.fail=true;
  nv.waitFor(db::Event::FAULT);
  check(nv.controller.reason()==db::Reason::PERSISTENCE_FAULT && nv.store.pending,
        "NVS completion failure faked success");
}
void test_no_progress_and_invalid_id() {
  Fixture f;f.start();
  check(f.controller.start(0,3,f.obs)==db::Reason::INVALID_ID,"zero request id accepted");
  check(f.controller.start(0x1000000u,3,f.obs)==db::Reason::INVALID_ID,"ID over journal width accepted");
  f.waitFor(db::Event::BASELINE);f.waitFor(db::Event::COARSE);
  f.waitFor(db::Event::CLOSE);f.waitFor(db::Event::MEASUREMENT);
  f.waitFor(db::Event::COARSE);f.waitFor(db::Event::CLOSE);f.waitFor(db::Event::FAULT);
  check(f.controller.reason()==db::Reason::NO_PROGRESS && !f.out.attached && f.store.pending,
        "empty hopper repeatedly pulsed despite no progress");
  Fixture drop;drop.start();drop.waitFor(db::Event::BASELINE);drop.waitFor(db::Event::COARSE);
  drop.waitFor(db::Event::CLOSE);drop.obs.grams=1.5f;
  drop.waitFor(db::Event::MEASUREMENT);drop.waitFor(db::Event::FINE);
  drop.waitFor(db::Event::CLOSE);drop.obs.grams=1.0f;
  drop.waitFor(db::Event::FAULT);
  check(drop.controller.reason()==db::Reason::INVALID_READING && drop.store.pending &&
        !drop.out.attached,"stable bowl-weight drop was blindly topped up");
}
int main() {
  try {
    case_run("target_already_reached",test_target_already_reached);
    case_run("normal_coarse_fine_overshoot",test_multipulse_coarse_fine);
    case_run("hx_notready_uncalibrated_invalid_target_disarmed",test_faults);
    case_run("baseline_unstable",test_baseline_unstable);
    case_run("scale_unstable",test_scale_unstable);
    case_run("pulse_time_gram_limits",test_limits);
    case_run("abort_duplicate_reboot_lock",test_abort_duplicate_persistence);
    case_run("hx_pwm_persistence_faults",test_sensor_fault_and_pwm);
    case_run("no_progress_and_invalid_id",test_no_progress_and_invalid_id);
    std::cout<<"DISPENSE_POLICY named="<<named<<" assertions="<<assertions
             <<" PHYSICAL_NOT_TESTED\n";
    return 0;
  } catch(const std::exception& e) { std::cerr<<"DISPENSE_POLICY_FAIL "<<e.what()<<'\n'; return 1; }
}
