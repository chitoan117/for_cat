from pathlib import Path
import sys,difflib
r=Path(__file__).parent
duration=int(sys.argv[1]);assert 100<=duration<=5000
for name in ('current','deployed'):
 src=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino') if name=='current' else r.parent/'servo_button_20261106/deployed/esp32/esp32.ino'
 raw=src.read_bytes();s=raw.decode('utf-8').replace('\r\n','\n');old=s
 a='uint16_t close_ms = 900; // Actual UNO CLOSE_MS, owner-tested mechanism.'
 assert s.count(a)==1
 s=s.replace(a,f'uint16_t close_ms = {duration}; // Closing-duration calibration: owner reports short closing, neutral stationary.')
 s=s.replace('3/servo_open=RIGHT 1400us 1100ms; 4/servo_close=LEFT 1600us 900ms',f'3/servo_open=RIGHT 1400us 1100ms; 4/servo_close=LEFT 1600us {duration}ms')
 s=s.replace('close_ms 900',f'close_ms {duration}')
 s=s.replace('CLOSE LEFT 1600us/900ms',f'CLOSE LEFT 1600us/{duration}ms')
 s=s.replace('// Duplicate close requests must not restart the 900ms timer.','// Duplicate close requests must not restart the configured closing timer.')
 s=s.replace('UNO: servo_uno restores tested timings;', 'UNO: servo_uno explicitly restores original 1100/900ms;')
 out=r/str(duration)/name;out.mkdir(parents=True,exist_ok=True)
 (out/'before.ino').write_bytes(raw);(out/'esp32').mkdir(exist_ok=True)
 (out/'esp32/esp32.ino').write_text(s,encoding='utf-8')
 (out/'change.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before',tofile='after')),encoding='utf-8')
 # Reuse extracted, already-tested servo definitions and branches; exercise the new timing boundary.
 test=(r.parent/'servo_button_20261106'/name/'test_servo.py').read_text(encoding='utf-8')
 start=test.index("h+=r'''\nuint32_t expectedDuty")
 end=test.index("(root/'servo_test.cpp')")
 main=r"""
h+=r'''
uint32_t expectedDuty(unsigned us){return (us*16384u+10000u)/20000u;}
void assertStopped(){assert(hw_attached&&!pwm.moving()&&duty==expectedDuty(1500));}
int main(){
 assert(open_ms==1100&&close_ms==TRIAL_CLOSE_MS);
 assert(SERVO_OPEN_US==1400&&SERVO_CLOSE_US==1600&&SERVO_NEUTRAL_US==1500);
 uint32_t t=10000;
 for(unsigned i=0;i<5;++i){
   assert(manualServoMove(true,open_ms,t));
   diagTick(t+open_ms-1);assert(pwm.moving());diagTick(t+open_ms);assertStopped();
   unsigned old=writes;assert(!manualServoMove(true,open_ms,t+open_ms+1)&&old==writes);
   uint32_t close_at=t+open_ms+100;
   assert(manualServoMove(false,close_ms,close_at));
   diagTick(close_at+close_ms-1);assert(pwm.moving());diagTick(close_at+close_ms);assertStopped();
   assert(timed_gate_stop==TimedGateStop::CLOSED);
   old=writes;assert(!manualServoMove(false,close_ms,close_at+close_ms+1)&&old==writes);
   t=close_at+close_ms+100;
 }
 scale_ready=true;scale_value=0;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 last_delta_g=0.1f;beginManualFeed(t+open_ms+100,"BUTTON");
 closingTick(t+open_ms+100+close_ms-1);assert(pwm.moving());
 closingTick(t+open_ms+100+close_ms);assertStopped();
 assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required);
 t+=open_ms+close_ms+200;beginManualFeed(t,"BUTTON");assert(pwm.moving());
 cancel("STOP",false);assertStopped();assert(cat_inspect_required);
 auto old=writes;beginManualFeed(t+100,"BUTTON");assert(writes==old);
 puts("PASS:new closing duration boundary;5 alternating cycles;no extra duplicate strokes;manual early-close retry;STOP lock;neutral and loadcell mass result preserved");
}
'''
""".replace('TRIAL_CLOSE_MS',str(duration))
 (out/'test_servo.py').write_text(test[:start]+main+test[end:],encoding='utf-8')
print('Staged candidate only:',duration,'ms. Live setting is RAM-only until physical acceptance.')
