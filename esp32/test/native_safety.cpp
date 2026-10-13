// Standalone C++ host assertions; no GPIO or real device is opened.
#include <cassert>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include "safety_logic.h"
#include "sensor_drivers.h"
#include "uart_v1.h"
#include "command_dispatch.h"
#include "board_config.h"
#include "pins.h"
#include "safety_record_codec.h"

using namespace safety;
static int passed_checks = 0;
#undef assert
#define assert(expr) do { ++passed_checks; if (!(expr)) { \
  std::fprintf(stderr, "HOST C++ FAIL: %s:%d: %s\n", __FILE__, __LINE__, #expr); \
  return 1; \
} } while (0)

class TestStore final : public DailyStore {
 public:
  DailyRecord saved{};
  bool working = true;
  bool save(const DailyRecord& value) override {
    if (!working) return false;
    saved = value;
    return true;
  }
};

class StaleSensor final : public drivers::Sensor<float> {
 public:
  drivers::Sample<float> poll(uint32_t) override { return {Health::OK, 10.0f, 0}; }
};

FeedInputs ready() {
  FeedInputs in;
  in.day = 20260930; in.epoch_seconds = 100000;
  in.rtc_valid = true; in.food_available = true;
  in.scale = Health::OK; in.servo = Health::OK;
  return in;
}

std::string asHex(const uint8_t* bytes, size_t size) {
  const char* digits = "0123456789abcdef";
  std::string result;
  for (size_t i = 0; i < size; ++i) {
    result.push_back(digits[bytes[i] >> 4]);
    result.push_back(digits[bytes[i] & 15]);
  }
  return result;
}

int main(int argc, char** argv) {
  drivers::SimSensor<float> sim_scale;
  sim_scale.set(10.0f);
  assert(sim_scale.poll(10).health == Health::OK);
  drivers::UnvalidatedSensor<float> unknown_scale;
  assert(unknown_scale.poll(10).health == Health::NOT_VALIDATED);
  StaleSensor stale;
  drivers::FreshnessCheckedSensor<float> bounded(stale, 50);
  assert(bounded.poll(100).health == Health::FAULT);
  drivers::ButtonDebouncer button;
  assert(!button.update(true, 0));
  assert(button.update(true, 40));
  assert(!button.update(true, 80));
  drivers::SimDisplay display;
  display.show("SAFE_BOOT");
  assert(display.health() == Health::OK && display.message()[0] == 'S');
  drivers::SimBuzzer buzzer;
  buzzer.alert();
  assert(buzzer.alerts() == 1);
  FeedInputs in = ready();
  FeedController feed;
  TestStore store;
  feed.attachStore(store);
  feed.boot({});
  assert(feed.state() == FeedState::SAFE_BOOT && !feed.openRequested());
  assert(feed.request(1, 10, in) && feed.reason() == FeedReason::SAFE_MODE);
  feed.boot({}); feed.tick(in);
  assert(feed.request(2, 10, in) && feed.state() == FeedState::PRECHECK);
  feed.tick(in);
  assert(feed.state() == FeedState::DISPENSING && feed.openRequested() && feed.record().needs_inspection);
  assert(store.saved.needs_inspection);
  assert(!feed.request(3, 10, in));  // busy cannot erase operation 2
  in.measured_grams = 10; in.now_ms = 100;
  feed.tick(in);
  assert(feed.state() == FeedState::CLOSING && !feed.openRequested());
  in.servo_closed = true; feed.tick(in);
  assert(feed.state() == FeedState::COMPLETE && feed.record().portions == 1 &&
         !feed.record().needs_inspection);
  assert(!store.saved.needs_inspection && store.saved.portions == 1);
  DailyRecord persisted = feed.record();
  feed.boot(persisted); feed.tick(in);
  assert(feed.record().portions == 1 && !feed.openRequested());
  assert(feed.request(4, 10, in) && feed.reason() == FeedReason::COOLDOWN);
  in.epoch_seconds += 3600;
  in.food_available = false;
  assert(feed.request(5, 10, in) && feed.reason() == FeedReason::FOOD_EMPTY);
  in.food_available = true; in.scale = Health::FAULT;
  assert(feed.request(6, 10, in) && feed.reason() == FeedReason::HX711_FAULT);
  in.scale = Health::OK; in.rtc_valid = false;
  assert(feed.request(7, 10, in) && feed.reason() == FeedReason::RTC_INVALID);
  in.rtc_valid = true; in.servo = Health::FAULT;
  assert(feed.request(8, 10, in) && feed.reason() == FeedReason::SERVO_FAULT);
  in.servo = Health::OK;
  DailyRecord limit{}; limit.day = in.day; limit.portions = 4;
  feed.boot(limit); feed.tick(in);
  assert(feed.request(9, 10, in) && feed.reason() == FeedReason::DAILY_PORTIONS);
  limit.portions = 0; limit.grams = 148;
  feed.boot(limit); feed.tick(in);
  assert(feed.request(10, 10, in) && feed.reason() == FeedReason::DAILY_GRAMS);
  feed.boot({}); feed.tick(in); in.now_ms = 0; in.measured_grams = 0;
  assert(feed.request(11, 10, in)); feed.tick(in);
  in.now_ms = 5000; feed.tick(in);
  assert(feed.state() == FeedState::FAULT && feed.reason() == FeedReason::NO_PROGRESS);
  assert(!feed.request(13, 10, in));  // fault latches until inspection
  DailyRecord interrupted = feed.record();
  feed.boot(interrupted); feed.tick(in);
  assert(feed.state() == FeedState::SAFE_BOOT && !feed.openRequested());
  feed.boot({}); feed.tick(in);
  assert(feed.request(12, 10, in)); feed.tick(in);
  in.now_ms += 20000; feed.tick(in);
  assert(feed.state() == FeedState::FAULT && feed.reason() == FeedReason::TIMEOUT);
  feed.boot({}); feed.tick(in);
  assert(feed.request(14, 10, in));
  store.working = false;
  feed.tick(in);
  assert(feed.state() == FeedState::FAULT && !feed.openRequested() &&
         feed.reason() == FeedReason::PERSISTENCE_FAULT);
  store.working = true;
  DailyRecord next_day{}; next_day.day = 20260930;
  next_day.portions = 4; next_day.grams = 140;
  feed.boot(next_day);
  in.day = 20261001; in.epoch_seconds += 86400;
  feed.tick(in);
  assert(feed.state() == FeedState::IDLE && feed.record().day == in.day &&
         feed.record().portions == 0 && feed.record().grams == 0);
  assert(store.saved.day == in.day && store.saved.portions == 0);

  WaterController water;
  WaterInputs w{}; w.sensor = Health::OK; w.pump = Health::OK; w.level_percent = 80;
  water.boot(); assert(!water.pumpRequested());
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::NORMAL);
  w.level_percent = 20;
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::FILLING && water.pumpRequested());
  w.level_percent = 80; water.tick(w);
  assert(water.state() == WaterState::NORMAL && !water.pumpRequested());
  w.sensor = Health::FAULT; water.tick(w);
  assert(water.state() == WaterState::FAULT && !water.pumpRequested());
  w.sensor = Health::OK;
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::NORMAL);
  w.pump = Health::FAULT; w.level_percent = 20;
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::FAULT && water.reason() == WaterReason::PUMP_FAULT &&
         !water.pumpRequested());
  water.boot(); w.pump = Health::OK; w.level_percent = 80;
  for (int i = 0; i < 3; ++i) water.tick(w);
  w.level_percent = 20;
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::FILLING && water.pumpRequested());
  w.now_ms = 5000; water.tick(w);
  assert(water.state() == WaterState::FAULT && water.reason() == WaterReason::NO_PROGRESS &&
         !water.pumpRequested());
  water.boot();
  assert(water.state() == WaterState::SAFE_BOOT && !water.pumpRequested());
  w.now_ms = 0; w.level_percent = 80;
  for (int i = 0; i < 3; ++i) water.tick(w);
  w.level_percent = 20;
  for (int i = 0; i < 3; ++i) water.tick(w);
  assert(water.state() == WaterState::FILLING);
  const uint32_t times[] = {4000u, 8000u, 12000u, 16000u, 20000u, 24000u, 28000u};
  for (uint32_t at : times) {
    w.now_ms = at;
    w.level_percent += 2;
    water.tick(w);
    assert(water.state() == WaterState::FILLING);
  }
  w.now_ms = 30000;
  water.tick(w);
  assert(water.state() == WaterState::FAULT && water.reason() == WaterReason::TIMEOUT &&
         !water.pumpRequested());

  dispatch::MemoryDailyStore twin_store;
  dispatch::Controller twin(true);
  auto sim_input = ready();
  safety::WaterInputs sim_water{};
  twin.boot(twin_store, twin_store.value, sim_input);
  auto accepted = twin.command(42, uart_v1::FEED_REQUEST, sim_input);
  assert(accepted.command == uart_v1::ACK && accepted.value == uart_v1::FEED_REQUEST);
  assert(twin.command(42, uart_v1::FEED_STATUS, sim_input).value == 0);
  twin.tick(sim_input, sim_water);
  sim_input.now_ms = 1000; sim_input.measured_grams = 10;
  twin.tick(sim_input, sim_water);
  sim_input.servo_closed = true;
  twin.tick(sim_input, sim_water);
  assert(twin.command(42, uart_v1::FEED_STATUS, sim_input).value == 1);
  assert(twin.command(42, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::ACK);
  assert(twin.feed.record().portions == 1); // duplicate ID doesn't dispense twice
  assert(twin.command(43, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::ACK);
  assert(twin.command(43, uart_v1::FEED_STATUS, sim_input).value == 2); // cooldown
  dispatch::Controller safe_build(false);
  safe_build.boot(twin_store, twin_store.value, sim_input);
  assert(safe_build.command(1, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::ACK);

  uint8_t record_bytes[safety_record::SIZE];
  safety::DailyRecord persisted_rc2 = twin.feed.record();
  assert(safety_record::encode(persisted_rc2, record_bytes));
  safety::DailyRecord restored_rc2{};
  assert(safety_record::decode(record_bytes, restored_rc2));
  assert(restored_rc2.portions == 1 && restored_rc2.grams == 10 &&
         restored_rc2.day == sim_input.day && restored_rc2.last_feed_epoch == sim_input.epoch_seconds);
  record_bytes[9] ^= 1;
  assert(!safety_record::decode(record_bytes, restored_rc2));
  assert(restored_rc2.portions == 1); // decoder didn't overwrite on corruption
  record_bytes[2] = 99;
  assert(!safety_record::decode(record_bytes, restored_rc2));

  safety::FeedController freshness;
  dispatch::MemoryDailyStore fresh_store;
  auto changed_input = ready();
  freshness.attachStore(fresh_store); freshness.boot({}); freshness.tick(changed_input);
  assert(freshness.request(70, 10, changed_input));
  changed_input.food_available = false;
  freshness.tick(changed_input);
  assert(freshness.state() == safety::FeedState::FAULT && !freshness.openRequested());
  safety::WaterController pump_health;
  safety::WaterInputs low{0, safety::Health::OK, safety::Health::OK, 20};
  for (int i = 0; i < 5; ++i) pump_health.tick(low);
  assert(pump_health.pumpRequested());
  low.pump = safety::Health::FAULT; pump_health.tick(low);
  assert(!pump_health.pumpRequested() && pump_health.reason() == safety::WaterReason::PUMP_FAULT);
  assert(safe_build.command(1, uart_v1::FEED_STATUS, sim_input).value == 2);
  assert(std::string(safe_build.reason()) == "SAFE_BUILD_ACTUATORS_DISABLED");
  assert(!safe_build.feed.openRequested() && !safe_build.water.pumpRequested());
  assert(pins::SERVO_PWM == pins::PIN_NOT_ASSIGNED && !board_profile::physical_outputs);
  for (uint32_t id = 2; id <= dispatch::Controller::capacity; ++id)
    assert(safe_build.command(id, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::ACK);
  assert(safe_build.command(17, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::NACK);
  assert(safe_build.command(1, uart_v1::FEED_REQUEST, sim_input).command == uart_v1::ACK);

  assert(argc == 2);  // one canonical CSV, supplied by check script
  std::ifstream input(argv[1]);
  assert(input.good());
  std::string line;
  assert(static_cast<bool>(std::getline(input, line)));
  assert(line == "name,request_id,command,payload_hex,crc_le_hex,frame_hex");
  int vectors = 0;
  while (std::getline(input, line)) {
    std::stringstream columns(line);
    std::vector<std::string> fields;
    std::string field;
    while (std::getline(columns, field, ',')) fields.push_back(field);
    assert(fields.size() == 6);
    const uint32_t id = static_cast<uint32_t>(std::stoul(fields[1], nullptr, 16));
    const uint8_t command = static_cast<uint8_t>(std::stoul(fields[2]));
    assert(fields[3].size() % 2 == 0 && fields[3].size() / 2 <= uart_v1::MAX_PAYLOAD);
    uint8_t payload[uart_v1::MAX_PAYLOAD];
    const size_t payload_size = fields[3].size() / 2;
    for (size_t i = 0; i < payload_size; ++i)
      payload[i] = static_cast<uint8_t>(std::stoul(fields[3].substr(i * 2, 2), nullptr, 16));
    uint8_t encoded[uart_v1::MAX_FRAME];
    size_t written = 0;
    assert(uart_v1::encode(id, command, payload, static_cast<uint16_t>(payload_size),
                           encoded, sizeof(encoded), written));
    assert(asHex(encoded, written) == fields[5]);
    assert(asHex(encoded + written - 2, 2) == fields[4]);
    assert(uart_v1::crc16(encoded + 2, written - 4) ==
           (static_cast<uint16_t>(encoded[written - 2]) |
            static_cast<uint16_t>(encoded[written - 1]) << 8));
    ++vectors;
  }
  assert(vectors == 7);
  std::printf("HOST C++ LOGIC VERIFIED: %d checks passed, 0 failed; %d UART v1 vectors match\n",
              passed_checks, vectors);
  return 0;
}
