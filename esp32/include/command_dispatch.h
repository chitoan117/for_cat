#pragma once
#include "safety_logic.h"
#include "uart_v1.h"

namespace dispatch {
struct Reply {
  uint32_t id;
  uint8_t command;
  uint8_t value;
};
struct FeedSlot {
  uint32_t id = 0;
  uint8_t result = 0; // UART v1: pending=0, success=1, rejected=2, error=3
};

class MemoryDailyStore final : public safety::DailyStore {
 public:
  safety::DailyRecord value{};
  bool working = true;
  bool save(const safety::DailyRecord& next) override {
    if (!working) return false;
    value = next;
    return true;
  }
};

// Host-testable dispatcher used by actual main.cpp. Neither mode drives pins.
class Controller {
 public:
  explicit Controller(bool simulation) : simulation_(simulation) {}
  void boot(safety::DailyStore& store, safety::DailyRecord record,
            const safety::FeedInputs& input) {
    feed.attachStore(store);
    feed.boot(record);
    water.boot();
    if (simulation_) feed.tick(input);
    used_ = 0; // never resume/replay an interrupted operation after reboot
  }
  Reply command(uint32_t id, uint8_t kind, const safety::FeedInputs& input) {
    if (kind == uart_v1::PING) return {id, uart_v1::ACK, uart_v1::PING};
    if (kind == uart_v1::GET_STATUS) return {id, uart_v1::SYSTEM_STATUS, 1};
    if (kind == uart_v1::FEED_STATUS) {
      auto slot = find(id);
      return slot ? Reply{id, uart_v1::FEED_STATUS, slot->result}
                  : Reply{id, uart_v1::NACK, 5};
    }
    if (kind != uart_v1::FEED_REQUEST) return {id, uart_v1::NACK, 3};
    if (id == 0) return {id, uart_v1::NACK, 6};
    if (find(id)) return {id, uart_v1::ACK, uart_v1::FEED_REQUEST};
    if (used_ == capacity) return {id, uart_v1::NACK, 4}; // fail closed, no eviction/re-execution
    if (simulation_ && !feed.request(id, simulated_target_grams, input))
      return {id, uart_v1::NACK, 4};
    slots_[used_++] = {id, static_cast<uint8_t>(simulation_ ? result() : 2)};
    return {id, uart_v1::ACK, uart_v1::FEED_REQUEST}; // never final success
  }
  void tick(const safety::FeedInputs& input, const safety::WaterInputs& water_input) {
    if (!simulation_) return;
    feed.tick(input);
    water.tick(water_input);
    if (auto slot = find(feed.requestId())) slot->result = result();
  }
  const char* reason() const {
    return simulation_ ? "SIMULATED_POLICY_RESULT" : "SAFE_BUILD_ACTUATORS_DISABLED";
  }
  safety::FeedController feed;
  safety::WaterController water;
  static constexpr float simulated_target_grams = 10; // local SIM default, NOT a v1 payload
  static constexpr size_t capacity = 16;
 private:
  FeedSlot* find(uint32_t id) {
    for (size_t i = 0; i < used_; ++i) if (slots_[i].id == id) return &slots_[i];
    return nullptr;
  }
  uint8_t result() const {
    switch (feed.state()) {
      case safety::FeedState::COMPLETE: return 1;
      case safety::FeedState::REJECTED: return 2;
      case safety::FeedState::FAULT: return 3;
      default: return 0;
    }
  }
  bool simulation_;
  FeedSlot slots_[capacity]{};
  size_t used_ = 0;
};
}  // namespace dispatch
