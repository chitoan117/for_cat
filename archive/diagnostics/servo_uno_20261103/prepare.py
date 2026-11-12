from pathlib import Path
import difflib
import hashlib

root=Path(__file__).parent
source=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino')
backup=root/'esp32.original.ino'
if backup.exists(): raise SystemExit('Backup exists; refusing to overwrite')
backup.write_bytes(source.read_bytes())
original=source.read_text(encoding='utf-8-sig')
code=original
def replace(old,new):
    global code
    if code.count(old)!=1: raise ValueError(f'Expected unique match: {old[:100]!r}')
    code=code.replace(old,new)

replace('constexpr uint16_t SERVO_OPEN_US = 1300;', 'constexpr uint16_t SERVO_OPEN_US = 1400; // UNO-tested: open RIGHT.')
replace('constexpr uint16_t SERVO_CLOSE_US = 1700;', 'constexpr uint16_t SERVO_CLOSE_US = 1600; // UNO-tested: close LEFT.')
replace('uint16_t open_ms = 550;   // SUPERVISED starting value, must bench-adjust\nuint16_t close_ms = 4000; // Timed close duration; inherited value, requires mechanical timing check.',
        'uint16_t open_ms = 1100; // Actual UNO OPEN_MS, not its outdated menu text.\nuint16_t close_ms = 900; // Actual UNO CLOSE_MS, owner-tested mechanism.\nconstexpr uint16_t SERVO_FINE_MS = 170; // Actual UNO FINE_MS.\nuint32_t servo_move_for_ms = 0;')
# Track rotation separately from an attached, neutral PWM output.
replace('    return ledcWrite(servo_bench::pin, duty);',
        '    const bool ok = ledcWrite(servo_bench::pin, duty);\n    if (ok) pulse_us_ = pulse_us;\n    return ok;')
replace('  bool attached() const {\n    return attached_;\n  }\n\n private:\n  static bool valid',
        '  bool attached() const {\n    return attached_;\n  }\n\n  bool moving() const {\n    return attached_ && pulse_us_ != 1500;\n  }\n\n private:\n  static bool valid')
replace('  bool attached_ = false;\n};\n\n}\n\n// ============================================================\n// NONBLOCKING UART0',
        '  bool attached_ = false;\n  uint16_t pulse_us_ = 0;\n};\n\n}\n\n// ============================================================\n// NONBLOCKING UART0')
# Existing idle/arming/calibration checks must allow neutral hold.
code=code.replace('pwm.attached()', 'pwm.moving()')
replace('void neutralMotor() {\n  if (pwm.moving()) {\n    pwm.write(SERVO_NEUTRAL_US);\n    pwm.off();\n  }\n}',
        'void neutralMotor() {\n  // Match UNO stopServo(): keep transmitting 1500 us after a movement.\n  // Detach only if the neutral command fails. Boot still starts detached.\n  if (pwm.attached() && !pwm.write(SERVO_NEUTRAL_US)) pwm.off();\n}')
replace('  if (!pwm.start(SERVO_NEUTRAL_US) || !pwm.write(SERVO_OPEN_US)) {',
        '  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US)) || !pwm.write(SERVO_OPEN_US)) {')
replace('  if (!pwm.moving() && !pwm.start(SERVO_NEUTRAL_US)) {',
        '  if (!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US)) {')
replace('void beginManualFeed(uint32_t now, const char* source) {',
        'void beginManualFeed(uint32_t now, const char* source) {\n  if (feed_stage == FeedStage::DIAG_OPEN || feed_stage == FeedStage::DIAG_CLOSE\n      || bench_cal != BenchCal::Idle) {\n    protocolSerial().print("MANUAL FEED BLOCKED: servo adjustment or calibration in progress.\\n");\n    return;\n  }')
# One shared timed motion function for manual full strokes and fine adjustment.
start=code.index('// Independent servo electrical test:')
end=code.index('\nvoid tick(const Sample& s, uint32_t now)',start)
code=code[:start]+'''// UNO-style nonblocking manual movement, sharing the feeder PWM owner.
bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {
  if (busy() || pwm.moving() || dog_running || bench_cal != BenchCal::Idle) {
    protocolSerial().print("SERVO BUSY: use 0 / stop to stop first.\\n");
    return false;
  }
  if (!duration || duration > MAX_SERVO_ACTIVE_MS) return false;
  if ((!pwm.attached() && !pwm.start(SERVO_NEUTRAL_US))
      || !pwm.write(opening ? SERVO_OPEN_US : SERVO_CLOSE_US)) {
    neutralMotor();
    protocolSerial().print("SERVO MANUAL OUTPUT FAILED; no timed move started.\\n");
    return false;
  }
  // Keep demo_exited / inspection lock unchanged: manual adjustment does not
  // authorize automatic CAT dispensing or establish a measured gate position.
  physical_closed_verified = false;
  servo_move_for_ms = duration;
  feed_stage = opening ? FeedStage::DIAG_OPEN : FeedStage::DIAG_CLOSE;
  phase_at = started_at = now;
  servo_armed = false;
  protocolSerial().printf("SERVO %s: GPIO6 pulse=%uus time=%lums; stop=1500us.\\n",
    opening ? "OPEN RIGHT" : "CLOSE LEFT",
    (unsigned)(opening ? SERVO_OPEN_US : SERVO_CLOSE_US), (unsigned long)duration);
  return true;
}

// Retain existing armed diagnostic aliases for compatibility.
void diagServo(bool opening, uint32_t now) {
  if (!servo_armed || cat_inspect_required) {
    protocolSerial().print("SERVO TEST BLOCKED: servo_arm / inspect_ok required.\\n");
    return;
  }
  manualServoMove(opening, opening ? open_ms : close_ms, now);
}
''' +code[end:]
replace('const uint32_t duration = feed_stage == FeedStage::DIAG_OPEN ? open_ms : close_ms;',
        'const uint32_t duration = servo_move_for_ms;')
replace('  // Only the supervised BENCH state machine handles numeric 0/1/2 commands.',
'''  // 1/2 retain CAT/DOG semantics used by Jetson; 3/4 are UNO full strokes.
  if (!std::strcmp(line, "3") || !std::strcmp(line, "servo_open")) {
    bench_v8::manualServoMove(true, bench_v8::open_ms, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "4") || !std::strcmp(line, "servo_close")) {
    bench_v8::manualServoMove(false, bench_v8::close_ms, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "servo_fine_close")) {
    bench_v8::manualServoMove(false, bench_v8::SERVO_FINE_MS, s.now_ms);
    return;
  }
  if (!std::strcmp(line, "servo_fine_open")) {
    bench_v8::manualServoMove(true, bench_v8::SERVO_FINE_MS, s.now_ms);
    return;
  }
  // Only the supervised BENCH state machine handles numeric 0/1/2 commands.''')
# Make a standalone 0 immediate even with the serial monitor set to no newline.
replace("      if (c == '\\r') continue;", """      if (c == '\\r') continue;
      if (c == '0' && rxn == 0 && !discard) {
        char stop_line[] = "0";
        command(stop_line, s);
        continue;
      }""")
replace('inspect_lock=%d servo_pwm=%d\\n', 'inspect_lock=%d servo_moving=%d\\n')
code=code.replace('servo PWM detached. Type start to re-enter.', 'servo held at 1500us. Type start to re-enter.')
code=code.replace('PWM neutral/off;', 'PWM held at 1500us;')
code=code.replace('manual bench servo OFF / buzzer OFF;', 'servo held at 1500us / buzzer OFF;')
code=code.replace('"TUNE: open_ms 550, close_ms 4000 (100..5000ms), idle only; stop\\n"',
    '"SERVO: 3/servo_open=RIGHT 1400us 1100ms; 4/servo_close=LEFT 1600us 900ms\\n"\n      "FINE: servo_fine_close / servo_fine_open = 170ms; 0/stop = hold 1500us\\n"\n      "TUNE: open_ms 1100, close_ms 900 (100..5000ms), idle only; stop\\n"')
code=code.replace('//   open_ms 550 / close_ms 4000;', '//   open_ms 1100 / close_ms 900;')
code=code.replace('1300us OPEN direction, 1700us CLOSE direction.', '1400us OPEN RIGHT, 1600us CLOSE LEFT (UNO-tested).')
code=code.replace('//   open_ms 1100 / close_ms 900; timed closure selected, GPIO47 disabled.',
    '//   open_ms 1100 / close_ms 900; 3=open, 4=close, servo_fine_open/close=170ms.\n//   GPIO47 disabled; 1/2 retain CAT/DOG commands; standalone 0 stops immediately.')
# Make the boot menu identify the loaded servo calibration.
replace('"Servo GPIO6, buzzer GPIO2. TIMED CLOSE; GPIO47 disabled; physical position UNKNOWN.\\n"',
        '"SERVO UNO PROFILE: GPIO6 OPEN RIGHT 1400us/1100ms, CLOSE LEFT 1600us/900ms, FINE 170ms, STOP 1500us.\\n"\n    "TIMED CLOSE; GPIO47 disabled; physical position UNKNOWN.\\n"')
out=root/'esp32/esp32.ino'
out.parent.mkdir(exist_ok=True)
out.write_text(code,encoding='utf-8',newline='\r\n')
(root/'change.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),code.splitlines(True),fromfile=str(source),tofile=str(out))),encoding='utf-8')
print('Backup SHA256:',hashlib.sha256(backup.read_bytes()).hexdigest())
print('Candidate SHA256:',hashlib.sha256(out.read_bytes()).hexdigest())
