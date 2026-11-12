from pathlib import Path
import difflib
r=Path(__file__).parent;prev=r.parent/'servo_relative_20261106'
for name in ('current','deployed'):
 src=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino') if name=='current' else prev/'deployed/esp32/esp32.ino'
 raw=src.read_bytes();s=raw.decode('utf-8').replace('\r\n','\n');old=s
 a='      cat_inspect_required = !close_on_weight && !hit_limit;'
 b='''      // In timed mode a FULL close stroke restores the relative CLOSED estimate.
      // An insufficient dose remains a feed FAULT below; it is not an interrupted servo.
      cat_inspect_required = USE_CLOSE_LIMIT_SWITCH && !hit_limit;'''
 assert s.count(a)==1;s=s.replace(a,b)
 out=r/name;out.mkdir(exist_ok=True);(out/'before.ino').write_bytes(raw)
 (out/'esp32').mkdir(exist_ok=True);(out/'esp32/esp32.ino').write_text(s,encoding='utf-8')
 (out/'change.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before',tofile='after')),encoding='utf-8')
 test=(prev/name/'test_servo.py').read_text(encoding='utf-8')
 marker=' puts("PASS:200 alternating cycles'
 extra=''' // Regression of the owner's exact button sequence: OPEN, early CLOSE, OPEN again.
 scale_ready=true;scale_value=0;
 for(uint32_t t=10000;t<76000;t+=2200){
   scale_stamp=t;beginManualFeed(t,"BUTTON_GPIO21");assert(feed_stage==FeedStage::OPENING);
   openingTick(t+1100);assertStopped();assert(feed_stage==FeedStage::WAIT_WEIGHT);
   last_delta_g=0.1f;beginManualFeed(t+1200,"BUTTON_GPIO21");
   assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
   closingTick(t+2100);assertStopped();
   assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required&&timed_gate_stop==TimedGateStop::CLOSED);
 }
 // A 4s manual timeout likewise stays a mass FAULT, but a full timed close is repeatable.
 beginManualFeed(100000,"BUTTON_GPIO21");openingTick(101100);
 scale_value=0.1f;scale_stamp=105100;weightTick(105100);
 assert(feed_stage==FeedStage::CLOSING&&!close_on_weight);
 closingTick(106000);assertStopped();assert(feed_stage==FeedStage::FAULT&&!cat_inspect_required);
 beginManualFeed(107000,"BUTTON_GPIO21");assert(pwm.moving());
 cancel("STOP MID-STROKE",false);before=writes;
 beginManualFeed(107100,"BUTTON_GPIO21");
 assert(cat_inspect_required&&timed_gate_stop==TimedGateStop::UNKNOWN&&writes==before);
 puts("PASS:30 consecutive physical-button sequences OPEN/early-CLOSE/next-OPEN;4s no-mass timeout allows retry after full close; interrupted motion still locks");
'''
 assert marker in test;test=test.replace(marker,extra+marker)
 (out/'test_servo.py').write_text(test,encoding='utf-8')
helper=(prev/'deploy_servo.py').read_text(encoding='utf-8')
helper=helper.replace("r=Path('/home/toan/for_cat/evidence/servo_relative_20261106')","r=Path('/home/toan/for_cat/evidence/servo_button_20261106')")
helper=helper.replace("Path('/home/toan/for_cat/evidence/readiness_20261104/firmware/esp32.ino.bin')","Path('/home/toan/for_cat/evidence/servo_relative_20261106/esp32.ino.bin')")
helper=helper.replace('f0e91dcb650f96e9f494d011c493888211b9658e24a686898693c892ac273c79','d7054e255babead6620ddb9cbb67ebe8ddd080b0c335d10254efce05f79eea89')
(r/'deploy_servo.py').write_text(helper,encoding='utf-8')
print('Prepared one-expression servo-position lock fix; feeding mass result unchanged.')
