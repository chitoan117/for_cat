from pathlib import Path
import hashlib,difflib
r=Path(__file__).parent
inputs={
 'current':Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino'),
 'deployed':r.parent/'readiness_20261104/esp32/esp32.ino',
}
def replace(s,a,b,n=1):
 assert s.count(a)==n,(a,s.count(a)); return s.replace(a,b)
for name,path in inputs.items():
 out=r/name;out.mkdir(exist_ok=True)
 raw=path.read_bytes();(out/'before.ino').write_bytes(raw)
 s=raw.decode('utf-8').replace('\r\n','\n'); before=s
 # Remove the old diagnostic fine-adjust commands from the deployed baseline too.
 if 'SERVO_FINE_MS' in s:
  for opening,direction in [('true','open'),('false','close')]:
   s=replace(s,f'''  if (!std::strcmp(line, "servo_fine_{direction}")) {{
    bench_v8::manualServoMove({opening}, bench_v8::SERVO_FINE_MS, s.now_ms);
    return;
  }}
''','')
  s=replace(s,'constexpr uint16_t SERVO_FINE_MS = 170; // Actual UNO FINE_MS.\n','')
  s=replace(s,'//   open_ms 1100 / close_ms 900; 3=open, 4=close, servo_fine_open/close=170ms.','//   open_ms 1100 / close_ms 900; 3=open, 4=close; no fine-adjust commands.')
  s=replace(s,'      "FINE: servo_fine_close / servo_fine_open = 170ms; 0/stop = hold 1500us\\n"','      "STOP: 0/stop = hold 1500us\\n"')
  s=s.replace(', FINE 170ms, STOP 1500us.',', STOP 1500us.')
 marker='uint32_t servo_move_for_ms = 0;'
 s=replace(s,marker,marker+'''

// A completed timed stroke is only a software estimate, never position feedback.
enum class TimedGateStop : uint8_t { UNKNOWN, OPEN, CLOSED };
TimedGateStop timed_gate_stop = TimedGateStop::UNKNOWN;
''')
 s=replace(s,'  if (may_have_moved) cat_inspect_required = true;','''  if (may_have_moved) {
    cat_inspect_required = true;
    timed_gate_stop = TimedGateStop::UNKNOWN;
  }''')
 s=replace(s,'bool startOpen(uint32_t now) {','''bool startOpen(uint32_t now) {
  if (cat_inspect_required || timed_gate_stop == TimedGateStop::OPEN) {
    protocolSerial().print("SERVO OPEN BLOCKED: already timed-open or interrupted; inspect and confirm CLOSED with inspect_ok.\\n");
    cat_inspect_required = true;
    feed_stage = FeedStage::FAULT;
    return false;
  }
  timed_gate_stop = TimedGateStop::UNKNOWN;''')
 s=replace(s,'    cancel("LEDC SERVO START FAILED", true);','''    cat_inspect_required = true;
    cancel("LEDC SERVO START FAILED", true);''')
 s=replace(s,'void startClose(uint32_t now, bool by_weight) {','''void startClose(uint32_t now, bool by_weight) {
  // Duplicate close requests must not restart the 900ms timer.
  if (feed_stage == FeedStage::CLOSING) return;
  if (timed_gate_stop == TimedGateStop::CLOSED) {
    protocolSerial().print("SERVO CLOSE IGNORED: last full stroke already timed-closed.\\n");
    return;
  }
  timed_gate_stop = TimedGateStop::UNKNOWN;''')
 s=replace(s,'    physical_closed_verified = true;\n    cat_inspect_required = false;','''    physical_closed_verified = true;
    timed_gate_stop = TimedGateStop::CLOSED;
    cat_inspect_required = false;''')
 s=replace(s,'  buzzerStop();\n  demo_exited = false;\n  cat_inspect_required = false;','''  // A button/Web request must not erase the lock after an interrupted servo run.
  if (cat_inspect_required) {
    protocolSerial().print("MANUAL FEED BLOCKED: inspect the gate, align CLOSED, then inspect_ok.\\n");
    return;
  }
  buzzerStop();
  demo_exited = false;''')
 s=replace(s,'bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {','''bool manualServoMove(bool opening, uint32_t duration, uint32_t now) {
  if (cat_inspect_required) {
    protocolSerial().print("SERVO BLOCKED: interrupted run; align CLOSED and confirm inspect_ok.\\n");
    return false;
  }
  const auto target = opening ? TimedGateStop::OPEN : TimedGateStop::CLOSED;
  if (timed_gate_stop == target) {
    protocolSerial().print("SERVO IGNORED: same full stroke already completed; no extra rotation.\\n");
    return false;
  }''')
 s=replace(s,'  if (!duration || duration > MAX_SERVO_ACTIVE_MS) return false;','''  if (!duration || duration > MAX_SERVO_ACTIVE_MS) return false;
  timed_gate_stop = TimedGateStop::UNKNOWN;''')
 s=replace(s,'    protocolSerial().print("SERVO MANUAL OUTPUT FAILED; no timed move started.\\n");','''    cat_inspect_required = true;
    feed_stage = FeedStage::FAULT;
    protocolSerial().print("SERVO MANUAL OUTPUT FAILED; inspection required.\\n");''')
 # Store estimates only after a full duration, never on STOP/abort.
 s=replace(s,'''    if (hit_close_limit || uint32_t(now - phase_at) >= duration) {
      neutralMotor();''','''    if (hit_close_limit || uint32_t(now - phase_at) >= duration) {
      timed_gate_stop = feed_stage == FeedStage::DIAG_OPEN ? TimedGateStop::OPEN : TimedGateStop::CLOSED;
      neutralMotor();''')
 s=replace(s,'      feed_stage = FeedStage::WAIT_WEIGHT;\n      phase_at = now;','''      timed_gate_stop = TimedGateStop::OPEN;
      feed_stage = FeedStage::WAIT_WEIGHT;
      phase_at = now;''')
 s=replace(s,'      physical_closed_verified = hit_limit;','''      timed_gate_stop = TimedGateStop::CLOSED;
      physical_closed_verified = hit_limit;''')
 # inspect_ok is operator acknowledgement; it is not a measured endstop.
 s=replace(s,'    bench_v8::cat_inspect_required = false;\n    bench_v8::feed_stage = bench_v8::FeedStage::IDLE;','''    bench_v8::cat_inspect_required = false;
    bench_v8::timed_gate_stop = bench_v8::TimedGateStop::CLOSED;
    bench_v8::feed_stage = bench_v8::FeedStage::IDLE;''')
 s=replace(s,'BENCH INSPECT ACK: gate position is operator responsibility. CAT can be tried again with 1.','BENCH INSPECT ACK: operator confirms gate aligned CLOSED; this is not sensor feedback. CAT may resume.')
 # Servo-only readout; do not report physical CLOSED without feedback.
 marker='  // 1/2 retain CAT/DOG semantics used by Jetson; 3/4 are UNO full strokes.'
 s=replace(s,marker,'''  if (!std::strcmp(line,"servo_position")) {
    const auto p = bench_v8::timed_gate_stop;
    protocolSerial().printf("SERVO ESTIMATE=%s feedback=NONE inspect_lock=%d moving=%d open_ms=%u close_ms=%u\\n",
      p==bench_v8::TimedGateStop::OPEN ? "OPEN" : p==bench_v8::TimedGateStop::CLOSED ? "CLOSED" : "UNKNOWN",
      int(bench_v8::cat_inspect_required),int(pwm.moving()),unsigned(bench_v8::open_ms),unsigned(bench_v8::close_ms));
    return;
  }
'''+marker)
 s=replace(s,'      "STOP: 0/stop = hold 1500us\\n"','''      "STOP: 0/stop = hold 1500us; no fine adjustment\\n"
      "SERVO: duplicate full strokes ignored; servo_position shows estimate only\\n"
      "AFTER ABORT: align gate CLOSED by hand with servo power OFF, restore power, then inspect_ok\\n"''')
 assert 'servo_fine_' not in s and 'SERVO_FINE_MS' not in s
 # Confirm the loadcell implementation and water control have not changed.
 a=before.index('class Hx711Median3 {'); b=before.index('// EXISTING NVS CALIBRATION RECORD',a)
 assert before[a:b]==s[s.index('class Hx711Median3 {'):s.index('// EXISTING NVS CALIBRATION RECORD')]
 for marker in ('namespace pcb_levels {',):
  if marker in before:
   def block(t,m):
    a=t.index(m);i=t.index('{',a)+1;n=1
    while n:
     n+=(t[i]=='{')-(t[i]=='}');i+=1
    return t[a:i]
   assert block(before,marker)==block(s,marker)
 p=out/'esp32';p.mkdir(exist_ok=True);(p/'esp32.ino').write_text(s,encoding='utf-8')
 (out/'change.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='before',tofile='after')),encoding='utf-8')
 print(name,'baseline',hashlib.sha256(raw).hexdigest(),'new',hashlib.sha256(s.encode()).hexdigest())
