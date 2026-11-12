from pathlib import Path
import hashlib,difflib

r=Path(__file__).parent
source=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino')
backup=r/'esp32.before.ino'
assert not backup.exists(),'Do not overwrite the pre-audit backup'
backup.write_bytes(source.read_bytes())
original=source.read_text(encoding='utf-8-sig')
code=original
def change(old,new):
    global code
    assert code.count(old)==1,old[:100]
    code=code.replace(old,new)

change('''    startClose(now, true);
    return;
  }
  if (feed_stage == FeedStage::OPENING || feed_stage == FeedStage::CLOSING) {''',
'''    // A manual early close is not proof that a measured serving was reached.
    startClose(now, last_delta_g >= CLOSE_AT_G && last_delta_g <= MAX_NORMAL_G);
    return;
  }
  if (feed_stage == FeedStage::OPENING || feed_stage == FeedStage::CLOSING) {''')
change('''  if (benchScaleSample(now, g, sample_ms)) {
    baseline_g = g;
  } else if (hx.signed_grams.valid && std::isfinite(hx.signed_grams.value)) {
    baseline_g = hx.signed_grams.value;
  } else {
    baseline_g = 0.0f;
  }''',
'''  if (!benchScaleSample(now, g, sample_ms)) {
    protocolSerial().print("MANUAL FEED BLOCKED: HX711 needs a fresh calibrated measurement; no 0g fallback.\\n");
    return;
  }
  baseline_g = g;''')
change('''      protocolSerial().print("MANUAL FEED TIMED CYCLE COMPLETE -> CLOSING GATE.\\n");
      startClose(now, true);''',
'''      protocolSerial().print("MANUAL FEED MASS NOT REACHED WITHIN 4S -> BOUNDED CLOSE, RESULT NOT VERIFIED.\\n");
      startClose(now, false);''')
# Allow the bounded recovery close its own 900ms after the global wait expires.
change('  if (uint32_t(now - started_at) > 45000u) {',
       '  if (feed_stage != FeedStage::CLOSING && uint32_t(now - started_at) > 45000u) {')
change('''    // Read new HC1 RAW samples, not stale or smoothed old values.
    if (hc.raw.fresh''',
'''    // Read new HC1 RAW samples, not stale or smoothed old values.
    if (!hc.raw.valid) {
      cat_hits = 0;
      return;
    }
    if (hc.raw.fresh''')
change('''          protocolSerial().print("WARNING: OVER 40g DETECTED; closing immediately.\\n");
        startClose(now, true);''',
'''          protocolSerial().print("WARNING: OVER 40g DETECTED; closing immediately.\\n");
        startClose(now, last_delta_g <= MAX_NORMAL_G);''')
# Invalid fresh HC1 samples break a consecutive detection sequence.
change('''    if (hc.raw.fresh && hc.raw.valid && hc.raw.sampled_at_ms != last_hc_ms) {
      if (last_hc_ms && uint32_t(hc.raw.sampled_at_ms - last_hc_ms) > 800u)
        cat_hits = 0;
      last_hc_ms = hc.raw.sampled_at_ms;
      float distance = hc.raw.value;''',
'''    if (hc.raw.fresh && hc.raw.sampled_at_ms != last_hc_ms) {
      if (last_hc_ms && uint32_t(hc.raw.sampled_at_ms - last_hc_ms) > 800u)
        cat_hits = 0;
      last_hc_ms = hc.raw.sampled_at_ms;
      if (!hc.raw.valid) {
        cat_hits = 0;
        return;
      }
      float distance = hc.raw.value;''')
# Expose enough compact read-only information to diagnose detached HX711 safely.
change('  // Read-only commands remain available.',
'''  if (!std::strcmp(line, "hx_diag")) {
    protocolSerial().printf("HX_DIAG DT4=%d SCK5=%d health=%s reason=%s raw_valid=%d last_raw=%ld raw_ms=%lu calibrated=%d\\n",
      digitalRead(4), digitalRead(5), m4::name(hx.status.health), m4::name(hx.status.reason),
      int(hx.raw.valid), (long)hx.raw.value, (unsigned long)hx.raw.sampled_at_ms,
      int(hx.calibration.valid()));
    return;
  }
  // Read-only commands remain available.''')

def block(text,marker):
    a=text.index(marker); b=text.index('{',a); e=b+1; level=1
    while level:
        level+=(text[e]=='{')-(text[e]=='}'); e+=1
    return text[a:e]
for marker in ['class Hx711 {','struct ScaleCalibration {','class NvsCalibration {',
               'bool benchScaleSample(uint32_t now, float& grams, uint32_t& sample_ms) {']:
    assert block(original,marker)==block(code,marker),'Unexpected HX711 algorithm/calibration change'
for exact in ['SERVO_OPEN_US = 1400','SERVO_CLOSE_US = 1600','SERVO_NEUTRAL_US = 1500',
              'open_ms = 1100','close_ms = 900','SERVO_FINE_MS = 170','CLOSE_AT_G = 30.0f','USE_CLOSE_LIMIT_SWITCH = false']:
    assert exact in code
out=r/'esp32/esp32.ino'
out.parent.mkdir(exist_ok=True)
out.write_text(code,encoding='utf-8',newline='\r\n')
(r/'firmware.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),code.splitlines(True),fromfile='esp32.before.ino',tofile='esp32/esp32.ino')),encoding='utf-8')
print('HX711 driver/calibration unchanged; UNO servo profile unchanged')
print('SOURCE_SHA256',hashlib.sha256(out.read_bytes()).hexdigest())
