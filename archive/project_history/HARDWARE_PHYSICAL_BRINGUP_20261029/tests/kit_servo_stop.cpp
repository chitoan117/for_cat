#define main retained_servo_fixture_main
#include "../firmware/test/servo_bench_loop.cpp"
#undef main
int main(){try{
 setup();send("servo configure 1450 1550 1500 1550 CONFIRM");send("servo arm YES");send("servo open");
 expect(hw::ledc_attached,"fake fixture did not attach PWM");send("servo stop");
 expect(!hw::ledc_attached && bench.state()==m4::servo_bench::State::FAULT && bench.pulse()==0,"STOP not immediate PWM OFF latched");
 send("servo arm YES");expect(!hw::ledc_attached,"STOP allowed automatic re-arm");
 expect(hw::touches[7]==0 && hw::nvs_writes==0,"servo touched pump/NVS");
 std::cout<<"KIT_SERVO_STOP_PASS fake_LEDC_only=true physical_pass=false\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
