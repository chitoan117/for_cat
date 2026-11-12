#include "sim_support.h"
using namespace offline_demo;
int main(){
 try{
   Log log(1793145600000ULL);Clock clock("INOX_E2E");log.context(clock,"INOX_MASS_DIFFERENCE_ONLY");Harness h(clock,log);
   h.mass=h.empty_container_gross=95;h.enforce_empty_container=true;h.prepare();h.arrival("CAT");h.dispense();
   require(h.successes==1&&h.last_actual==35&&h.mass==130&&h.servo.angle==90,"bowl95+food35 must be gross130 / delta35");
   require(h.beginMeal("FOOD_A"),"bowl meal start");const auto start=clock.now;const auto opens=h.servo.opens;
   while(clock.now-start<60000){const auto dt=clock.now-start;h.mass=dt<20000?130:dt<45000?120:100;h.step();}
   require(h.preference_result.valid&&h.preference_result.consumed==30&&h.preference_result.remaining==5&&h.preference_result.classification=="LIKE"&&h.servo.opens==opens,"bowl removed twice or consumption refed");
   h.clearBowl();require(h.mass==95,"bowl clearing must retain inox mass");
   log.event("INOX_E2E_RESULT",{{"status",quote("PASS")},{"empty_bowl_gross","95"},{"gross_after_dispense","130"},{"actual_dispensed","35"},{"meal_end_gross","100"},{"consumed","30"},{"classification",quote("LIKE")},{"bowl_retained_after_clear","95"}});
   Clock other("INOX_LEFTOVERS");log.context(other,"LEFTOVER_BLOCK");Harness leftovers(other,log);leftovers.mass=100;leftovers.empty_container_gross=95;leftovers.enforce_empty_container=true;leftovers.prepare();leftovers.arrival("CAT");
   require(!leftovers.feeding&&!leftovers.servo.opens,"leftover5g silently accepted as empty");
   log.event("INOX_LEFTOVER_RESULT",{{"status",quote("PASS")},{"servo_open_count","0"}});return 0;
 }catch(const std::exception& e){std::cerr<<"INOX_E2E_FAIL "<<e.what()<<'\n';return 1;}
}
