from pathlib import Path
r=Path(__file__).parent
old=(r.parent/'readiness_20261104/test_servo.py').read_text(encoding='utf-8')
a=old.index("h+=r'''\nuint32_t expectedDuty")
b=old.index("(root/'servo_test.cpp')")
prefix=old[:a].replace("'SERVO_FINE_MS',",'')
prefix=prefix.replace("for marker in ['bool busy() {'", "h+=block('enum class TimedGateStop : uint8_t {')+';\\nTimedGateStop timed_gate_stop=TimedGateStop::UNKNOWN;\\n'\nfor marker in ['bool busy() {'")
tail=old[b:old.index('# Check command routing')]
tail=tail.replace("str(root.parent/'timed_close_20261103/zig-global-cache')", "r'D:\\Agent_Cat\\diagnostics\\timed_close_20261103\\zig-global-cache'")
main=r"""
h+='void confirmClosed() '+block('  if (!std::strcmp(line, "inspect_ok")) {').split('{',1)[1].join(['{','']).replace('bench_v8::','')+'\n'
h+=r'''
uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){
 assert(open_ms==1100&&close_ms==900);
 assert(SERVO_OPEN_US==1400&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
 assert(!pwm.attached()&&timed_gate_stop==TimedGateStop::UNKNOWN);
 // The unchanged startup policy allows a first isolated stroke from UNKNOWN.
 assert(manualServoMove(true,open_ms,100));
 assert(duty==expectedDuty(1400));
 assert(!manualServoMove(false,close_ms,200));
 beginManualFeed(200,"WEB"); assert(phase_at==100);
 diagTick(1199);assert(pwm.moving());diagTick(1200);assertStopped();
 assert(timed_gate_stop==TimedGateStop::OPEN);
 unsigned before=writes;
 assert(!manualServoMove(true,open_ms,1300)&&writes==before);
 assert(manualServoMove(false,close_ms,1400));
 diagTick(2299);assert(pwm.moving());diagTick(2300);assertStopped();
 assert(timed_gate_stop==TimedGateStop::CLOSED);
 before=writes;assert(!manualServoMove(false,close_ms,2400)&&writes==before);
 // No accumulating same-direction strokes across repeated button presses.
 for(uint32_t i=0;i<200;i++){
   uint32_t t=3000+i*2200;
   assert(manualServoMove(true,open_ms,t));diagTick(t+1100);assertStopped();
   before=writes;assert(!manualServoMove(true,open_ms,t+1101)&&writes==before);
   assert(manualServoMove(false,close_ms,t+1200));diagTick(t+2100);assertStopped();
   before=writes;assert(!manualServoMove(false,close_ms,t+2101)&&writes==before);
 }
 assert(manualServoMove(true,open_ms,500000));cancel("STOP",false);assertStopped();
 assert(cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN);
 before=writes;
 assert(!manualServoMove(true,open_ms,500100));assert(!manualServoMove(false,close_ms,500100));
 scale_ready=true;scale_value=0;beginManualFeed(500200,"WEB");
 assert(cat_inspect_required&&writes==before&&!pwm.moving());
 confirmClosed();assert(!cat_inspect_required&&timed_gate_stop==TimedGateStop::CLOSED);
 assert(!physical_closed_verified); // Manual acknowledgement never becomes sensor evidence.
 // Actual normal feeding still waits for the unchanged measured30g threshold.
 scale_ready=false;before=writes;beginManualFeed(501000,"WEB");assert(writes==before);
 scale_ready=true;scale_value=0;scale_stamp=502000;
 beginManualFeed(502000,"BUTTON");assert(feed_stage==FeedStage::OPENING);
 openingTick(503099);assert(pwm.moving());openingTick(503100);assertStopped();
 assert(timed_gate_stop==TimedGateStop::OPEN);
 scale_value=29;scale_stamp=503200;weightTick(503200);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=30;scale_stamp=503300;weightTick(503300);assert(feed_stage==FeedStage::CLOSING&&close_on_weight);
 auto close_started=phase_at;before=writes;startClose(503700,true);assert(phase_at==close_started&&writes==before);
 closingTick(504199);assert(pwm.moving());closingTick(504200);assertStopped();
 assert(feed_stage==FeedStage::DONE&&timed_gate_stop==TimedGateStop::CLOSED&&!physical_closed_verified);
 // A manual-open gate cannot receive a second opening through the Web/feed path.
 assert(manualServoMove(true,open_ms,505000));diagTick(506100);assertStopped();before=writes;
 beginManualFeed(506200,"WEB");assert(writes==before&&cat_inspect_required&&feed_stage==FeedStage::FAULT);
 confirmClosed();
 // millis wrap works with full strokes; no fine-adjust stroke is available.
 assert(manualServoMove(true,open_ms,UINT32_MAX-100));
 diagTick(998);assert(pwm.moving());diagTick(999);assertStopped();
 cancel("STOP",false); // idle full stop retains estimate, no partial movement.
 assert(manualServoMove(false,close_ms,2000));diagTick(2900);assertStopped();
 // Output failure requires inspection; it cannot silently authorize another stroke.
 assert(manualServoMove(true,open_ms,3000));fail_write=true;cancel("OUTPUT",true);
 assert(!pwm.attached()&&cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN);
 fail_write=false;confirmClosed();
 dog_running=true;assert(!manualServoMove(true,open_ms,5000));dog_running=false;
 bench_cal=BenchCal::Tare;assert(!manualServoMove(true,open_ms,5000));bench_cal=BenchCal::Idle;
 assert(gpio_reads==0); // No new endstop pin reads or hardware assumptions.
 puts("PASS:200 alternating cycles, duplicate same-direction rejection, full UNO pulses/timing, immediate STOP and interruption lock, manual feed cannot bypass inspection");
 puts("PASS:normal measured30g close, close timer not restarted, missing scale block, no fabricated physical closure, millis rollover, PWM failure and ownership guards");
}
'''
"""
for name in ('current','deployed'):
 (r/name/'test_servo.py').write_text(prefix+main+tail+"assert 'servo_fine_' not in code and 'SERVO_FINE_MS' not in code\nprint('PASS: fine adjustment removed')\n",encoding='utf-8')
print('Prepared tests extracting actual candidate functions for both source baselines.')
