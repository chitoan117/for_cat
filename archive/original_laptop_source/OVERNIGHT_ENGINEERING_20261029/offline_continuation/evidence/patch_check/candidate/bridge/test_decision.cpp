#include "decision_logic.h"
#include "feed_policy.h"
#include <iostream>
#include <stdexcept>
using namespace forcat;
int main(){
 unsigned checks=0;auto check=[&](bool value){++checks;if(!value)throw std::runtime_error("decision check "+std::to_string(checks));};
 try{
    AutoCatGate disabled;check(!disabled.update("CAT",true,true,10,1,0));check(!disabled.configured());
    AutoCatGate cat({30,1000,3}); // SYNTHETIC fixture only; NOT a production near threshold.
    check(!cat.update("CAT",true,true,20,1,0));check(!cat.update("CAT",true,true,20,2,500));
    check(cat.update("CAT",true,true,20,3,1000));check(cat.stable());
    check(!cat.update("CAT",true,true,20,4,1500)); // one candidate/session, not per frame
    check(!cat.update("CAT",true,true,40,5,2000));check(!cat.stable());
    check(!cat.update("CAT",true,true,20,6,2500));check(!cat.update("NONE",true,true,20,7,3000));
    check(!cat.update("CAT",true,true,20,8,3500)); // transient CAT never enough
    for(auto species:{"DOG","NONE"})check(!cat.update(species,true,true,10,9,5000));
    check(!cat.update("CAT",false,true,10,10,6000));check(!cat.update("CAT",true,false,10,11,7000));
    AutoCatGate repeated({30,1000,3});check(!repeated.update("CAT",true,true,20,1,0));
    check(!repeated.update("CAT",true,true,20,1,2000));check(!repeated.stable());
    AutoCatGate gap({30,1000,3});check(!gap.update("CAT",true,true,20,1,0));
    check(!gap.update("CAT",true,true,20,2,500));check(!gap.update("CAT",true,true,20,3,5000));check(!gap.stable());
    FeedArbiter arbiter;FeedEvidence e;e.species="CAT";e.observations_fresh=true;e.near_confirmed_stable=true;e.telemetry_safe=true;
    auto d=arbiter.evaluate({"candidate","AUTO_CAT","",35},e,1000);
    check(d.qualification_reason=="WEIGHT_NOT_CALIBRATED" && !d.actuator_execution);
    FoodBehaviorFsm behavior(1.0,1000);
    check(behavior.update(false,false,false,false,0,0)==FoodBehavior::IDLE);
    check(behavior.update(true,false,false,false,0,100)==FoodBehavior::APPROACHING);
    check(behavior.update(true,true,false,true,10,200)==FoodBehavior::NEAR_FOOD);
    for(unsigned i=0;i<8;++i)check(behavior.update(true,true,true,true,10.0+(i%2?.01:-.01),300+i*500)==FoodBehavior::NEAR_FOOD);
    check(behavior.update(true,true,true,true,8.0,5000)==FoodBehavior::NEAR_FOOD);
    check(behavior.update(true,true,true,true,7.0,5500)==FoodBehavior::EATING);
    check(behavior.update(false,false,true,true,7,6000)==FoodBehavior::LEAVING);
    check(behavior.update(false,false,true,true,7,6600)==FoodBehavior::IDLE);
    FoodBehaviorFsm uncal(1,1000);
    for(unsigned i=0;i<8;++i)check(uncal.update(true,true,false,true,10-i,1000*i)!=FoodBehavior::EATING);
    WaterDryRun unset;check(!unset.update(true,100,true,0));check(unset.reason()=="THRESHOLDS_UNCONFIGURED");
    WaterDryRun water({40,20,1000,2000}); // SYNTHETIC distances, never production defaults.
    check(!water.update(false,0,true,0));check(water.reason()=="INVALID_SENSOR_FAILSAFE_OFF");
    check(water.update(true,50,true,100));check(water.update(true,30,true,500)); // hysteresis
    check(!water.update(true,20,true,800));check(water.reason()=="TARGET_REACHED_OFF");
    check(!water.update(true,50,true,1000));check(water.reason()=="COOLDOWN");
    check(water.update(true,50,true,2000));check(!water.update(false,50,true,2100));
    check(!water.update(true,50,false,4000));check(water.reason()=="SAFETY_BLOCKED");
    check(water.update(true,50,true,5000));check(!water.update(true,50,true,7100));check(water.reason()=="MAX_RUNTIME_OFF");
    check(!water.actuator_execution); // no AI input or hardware interface exists in water policy
    TimeGate clock;check(!clock.update(1760000000000LL,1000,false));check(clock.update(1760000001000LL,2000,true));
    std::cout<<"Decision temporal/FSM/water: "<<checks<<" checks PASS; all synthetic; no hardware output\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
