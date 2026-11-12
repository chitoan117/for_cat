from pathlib import Path
r=Path(__file__).parent
p=r/'esp32/esp32.ino';s=p.read_text(encoding='utf-8')
a=s.index('void updateOLED(uint32_t now) {');b=s.index('\nvoid printSensorSummary(',a)
s=s[:a]+'''void updateOLED(uint32_t now) {
  if (!oled_ok || uint32_t(now - last_oled_ms) < 400) return;
  last_oled_ms = now;
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0,0);
  oled.print("CAN: ");
  if (hx.display_grams.valid) { oled.print(hx.display_grams.value,1); oled.print(" g"); }
  else oled.print("-- g");
  oled.setCursor(0,10);
  oled.print(bench_v8::stateText());
  drawDistance("E1 MEO:    ", recentCm(hc,now),20);
  drawDistance("E2 THUC AN:", recentCm(hc2,now),30);
  drawDistance("D1 CHEN:   ", recentCm(bowl_d1,now),40);
  drawDistance("D2 BINH:   ", recentCm(tank_d2,now),50);
  oled.display();
}
'''+s[b:]
p.write_text(s,encoding='utf-8')
t=r/'test_servo.py';test=t.read_text(encoding='utf-8')
marker=' puts("PASS:new closing duration boundary;'
extra=''' // Run the actual production weight branch at the new target boundary.
 cat_inspect_required=false;feed_stage=FeedStage::IDLE;timed_gate_stop=TimedGateStop::CLOSED;
 t=100000;scale_value=0;scale_ready=true;beginManualFeed(t,"BUTTON");openingTick(t+open_ms);
 scale_value=34.99f;++scale_stamp;weightTick(t+open_ms+1);assert(feed_stage==FeedStage::WAIT_WEIGHT);
 scale_value=35.0f;++scale_stamp;weightTick(t+open_ms+2);assert(feed_stage==FeedStage::CLOSING&&close_on_weight);
 closingTick(t+open_ms+2+close_ms);assertStopped();
 // Three distinct E1 readings are required; 30cm is accepted, >30cm rejected.
 cat_inspect_required=false;feed_stage=FeedStage::WAIT_CAT;timed_gate_stop=TimedGateStop::CLOSED;
 phase_at=200000;cat_hits=0;last_hc_ms=0;hc.raw.valid=hc.raw.fresh=true;
 hc.raw.value=30.01f;hc.raw.sampled_at_ms=200001;catTick(200001);assert(cat_hits==0);
 hc.raw.value=30.0f;
 for(unsigned i=1;i<=3;i++){hc.raw.sampled_at_ms=200001+180*i;catTick(hc.raw.sampled_at_ms);}
 assert(feed_stage==FeedStage::OPENING);cancel("STOP",false);
 puts("PASS: 34.99g waits,35g closes;E1 30cm accepted after3 distinct readings,30.01cm rejected");
'''
assert marker in test;test=test.replace(marker,extra+marker)
t.write_text(test,encoding='utf-8')
print('OLED labels updated; real branch mass/distance boundary tests added.')
