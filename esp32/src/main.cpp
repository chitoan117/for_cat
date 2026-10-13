#include <Arduino.h>
#include "hardware_interfaces.h"
#include "board_config.h"
#include "pins.h"
#include "safety_logic.h"
#include "sensor_drivers.h"
#include "safety_persistence.h"
#include "uart_v1.h"
#include "command_dispatch.h"
#include "serial_port.h"
#include "build_info.h"
#include "m4/diagnostic_config.h"

#if M4_DIAGNOSTIC_MODE == 0

// v1 protocol: A5 5A | version | request_id LE32 | command | length LE16
// | up to 256 payload bytes | CRC16/CCITT-FALSE LE16 over version..payload.
namespace {
constexpr uint8_t START_A = uart_v1::START_A, START_B = uart_v1::START_B;
constexpr uint8_t VERSION = uart_v1::VERSION;
constexpr size_t HEADER = uart_v1::HEADER, MAX_PAYLOAD = uart_v1::MAX_PAYLOAD;
constexpr size_t MAX_FRAME = uart_v1::MAX_FRAME;
constexpr unsigned long FRAME_TIMEOUT_MS = 250;
constexpr size_t MAX_BYTES_PER_LOOP = 64;
enum Command : uint8_t {
  PING = uart_v1::PING, GET_STATUS = uart_v1::GET_STATUS,
  FEED_REQUEST = uart_v1::FEED_REQUEST, FEED_STATUS = uart_v1::FEED_STATUS,
  SYSTEM_STATUS = uart_v1::SYSTEM_STATUS, ACK = uart_v1::ACK, NACK = uart_v1::NACK
};
enum FeedResult : uint8_t { PENDING = 0, SUCCESS = 1, REJECTED = 2, ERROR = 3 };
enum ErrorCode : uint8_t {
  BAD_FRAME = 1, BAD_VERSION = 2, UNSUPPORTED = 3, BUSY = 4,
  UNKNOWN_ID = 5, BAD_PAYLOAD = 6
};

uint32_t readId(const uint8_t* bytes) {
  return static_cast<uint32_t>(bytes[0]) |
         (static_cast<uint32_t>(bytes[1]) << 8) |
         (static_cast<uint32_t>(bytes[2]) << 16) |
         (static_cast<uint32_t>(bytes[3]) << 24);
}

void reply(uint32_t id, Command command, const uint8_t* payload, uint16_t length) {
  uint8_t frame[MAX_FRAME];
  size_t written = 0;
  if (uart_v1::encode(id, static_cast<uint8_t>(command), payload, length,
                      frame, sizeof(frame), written)) protocolSerial().write(frame, written);
}

void nack(uint32_t id, ErrorCode reason) {
  const uint8_t payload[] = {reason};
  reply(id, NACK, payload, 1);
}

#if defined(SIMULATED_SENSORS)
dispatch::Controller controller(true);
dispatch::MemoryDailyStore simulated_store;
#else
dispatch::Controller controller(false);
#endif
NvsSafetyStore nvs;
drivers::InertServo servo;
drivers::InertPump pump;
safety::FeedInputs inputs;
safety::WaterInputs water_inputs;
uint32_t last_sim_update = 0;

void sampleSimulation(uint32_t now) {
#if defined(SIMULATED_SENSORS)
  // Explicit digital-twin values: never passed to real GPIO/sensors/NVS.
  inputs.now_ms = now;
  inputs.epoch_seconds = 100000 + now / 1000;
  inputs.day = 20260101;
  inputs.rtc_valid = inputs.food_available = true;
  inputs.scale = inputs.servo = safety::Health::OK;
  if (static_cast<uint32_t>(now - last_sim_update) >= 250) {
    if (controller.feed.state() == safety::FeedState::DISPENSING)
      inputs.measured_grams += 1.0f;
    last_sim_update = now;
  }
  inputs.servo_closed = !controller.feed.openRequested();
  water_inputs = {now, safety::Health::OK, safety::Health::OK, 80.0f};
#else
  inputs.now_ms = now; // other fields remain invalid/NOT_VALIDATED
#endif
}

void handle(const uint8_t* frame, uint16_t length) {
  uint32_t id = readId(frame + 3);
  uint16_t payloadLength = static_cast<uint16_t>(frame[8]) |
                           (static_cast<uint16_t>(frame[9]) << 8);
  if (frame[2] != VERSION) { nack(id, BAD_VERSION); return; }
  if (payloadLength > MAX_PAYLOAD || length != HEADER + payloadLength + 2 ||
      uart_v1::crc16(frame + 2, HEADER - 2 + payloadLength) !=
          (static_cast<uint16_t>(frame[length - 2]) |
           (static_cast<uint16_t>(frame[length - 1]) << 8))) {
    nack(id, BAD_FRAME);
    return;
  }
  if (payloadLength != 0) { nack(id, BAD_PAYLOAD); return; }
  const auto response = controller.command(id, frame[7], inputs);
  reply(response.id, static_cast<Command>(response.command), &response.value, 1);
}

uint8_t buffer[MAX_FRAME];
uint16_t used = 0;
unsigned long lastByteAt = 0;

void acceptByte(uint8_t byte) {
  lastByteAt = millis();
  if (used == 0) {
    if (byte == START_A) buffer[used++] = byte;
    return;
  }
  if (used == 1 && byte != START_B) {
    used = 0;
    if (byte == START_A) buffer[used++] = byte;
    return;
  }
  if (used >= MAX_FRAME) { used = 0; return; }
  buffer[used++] = byte;
  if (used == HEADER) {
    uint16_t payloadLength = static_cast<uint16_t>(buffer[8]) |
                             (static_cast<uint16_t>(buffer[9]) << 8);
    if (payloadLength > MAX_PAYLOAD) {
      nack(readId(buffer + 3), BAD_FRAME);
      used = 0;
      return;
    }
  }
  if (used >= HEADER) {
    uint16_t expected = HEADER + static_cast<uint16_t>(buffer[8]) +
                        (static_cast<uint16_t>(buffer[9]) << 8) + 2;
    if (used == expected) {
      handle(buffer, used);
      used = 0;
    }
  }
}
}  // namespace

void setup() {
  protocolSerial().begin(115200);
#if defined(FORR_BUILD_BANNER) && FORR_BUILD_BANNER
  // Optional once-only ASCII boot banner for a human monitor. Host transport
  // discards startup bytes/scans binary START. No metadata added to v1 replies.
  protocolSerial().printf("FORR_CAT firmware=%s profile=%s board=%s actuator_enabled=%u simulation=%u "
                          "safety=SAFE_BUILD_ACTUATORS_DISABLED uart_version=1\r\n",
                          build_info::firmware_version, build_info::profile, build_info::board,
                          build_info::actuator_enabled ? 1u : 0u, build_info::simulation ? 1u : 0u);
#endif
  sampleSimulation(millis());
#if defined(SIMULATED_SENSORS)
  controller.boot(simulated_store, simulated_store.value, inputs);
#else
  safety::DailyRecord persisted;
  if (!nvs.load(persisted)) persisted.revision = 0;  // invalid state fails closed
  controller.boot(nvs, persisted, inputs);
#endif
  servo.requestOpen(false);
  pump.requestOn(false);
  // No actuator GPIO pins configured, even when a simulator desires output.
}

void loop() {
  sampleSimulation(millis());
  controller.tick(inputs, water_inputs);
  if (used != 0 && millis() - lastByteAt > FRAME_TIMEOUT_MS) used = 0;
  size_t processed = 0;
  while (processed < MAX_BYTES_PER_LOOP && protocolSerial().available() > 0) {
    acceptByte(static_cast<uint8_t>(protocolSerial().read()));
    ++processed;
  }
}
#endif  // normal protocol firmware never executes component diagnostics
