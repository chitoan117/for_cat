#define ARDUINO 10819
#define CONFIG_IDF_TARGET_ESP32S3 1
#define FORR_BOARD_S3 1
#define FORR_REAL_S3_NO_PSRAM 1
#define FORR_HW_SAFE 1
#define FORR_NATIVE_USB 0
#define ARDUINO_USB_CDC_ON_BOOT 0
#define M4_SENSOR_BRINGUP 1
#define M4_DIAGNOSTIC_MODE 1
#define M4_HX711_INSTALLED 1
#define SERVO_DIAGNOSTIC_ENABLED 0
#define PUMP_DIAGNOSTIC_ENABLED 0
#define CAT_FEED_DEMO 1
#define CAT_FEED_PHYSICAL_ENABLE 1
#include "../src/cat_feed_demo.cpp"
#include <iostream>
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL line"<<__LINE__<<": "<<#x<<"\n";return 1;}}while(0)
int main(){
  setup(); CHECK(!feed.initialized() && !feed.pending() && !calibration_loaded);
  command("stop");command("DOG");command("feed 1");
  CHECK(host_board::ledc_attaches==0 && host_board::touches[7]==0);
  command("calset -671054.666666667 -1064.4473 SAVE");
  CHECK(calibration_loaded && host_board::nvs_writes==1);
  command("journal init CONFIRM");CHECK(feed.initialized() && !feed.pending());
  setup();CHECK(calibration_loaded && feed.initialized() && !feed.pending()); // actual codec/key/reload
  auto adc=[](double g){const auto raw=static_cast<int32_t>(std::llround(-671054.666666667+g*-1064.4473));
    host_board::queue_adc(raw);host_board::now_us+=100000;command("cat 1");loop();};
  for(int i=0;i<3;++i)adc(-0.4);
  CHECK(scale.signed_grams.valid && scale.signed_grams.value<0);
  command("feed 1");CHECK(feed.state()==cf::State::BASELINE && journal.load(sequence)==Journal::PENDING);
  for(int i=0;i<15 && feed.state()==cf::State::BASELINE;++i)adc(-0.4);
  CHECK(feed.state()==cf::State::OPEN && host_board::ledc_attaches==1);
  CHECK(host_board::ledc_duty==(1000*65536u+10000u)/20000u);
  for(int i=0;i<60 && feed.active();++i)adc(34.7);
  CHECK(feed.state()==cf::State::COMPLETE && !pwm.attached() && !feed.pending());
  CHECK(feed.delta()>35 && feed.delta()<35.2);
  const auto opens=host_board::ledc_attaches;
  command("feed 1");command("feed 2");CHECK(host_board::ledc_attaches==opens); // one episode per boot
  CHECK(journal.write(true,2));setup();
  CHECK(feed.pending());command("feed 3");CHECK(host_board::ledc_attaches==opens);
  CHECK(host_board::touches[7]==0);
  for(int p=0;p<64;++p)if(p!=4 && p!=5 && p!=6)CHECK(host_board::touches[p]==0);
  CHECK(host_board::critical_depth==0 && host_board::critical_errors==0);
  std::cout<<"CAT_FEED_LOOP_PASS assertions="<<checks<<" fake_io_only=true\n";
}
