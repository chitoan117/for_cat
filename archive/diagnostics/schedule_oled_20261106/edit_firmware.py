from pathlib import Path
import re
r=Path(__file__).parent;s=(r/'before/esp32.ino').read_text()
a=s.index('const char* oledAiLineText(uint32_t now) {');b=s.index('\nvoid buzzerWrite(',a)
s=s[:a]+'''const char* oledAiLineText(uint32_t now) {
  if (ai_species_ms != 0 && uint32_t(now-ai_species_ms) <= AI_DISPLAY_HOLD_MS) {
    if(ai_species=='C') return "CAT";
    if(ai_species=='D') return "DOG";
  }
  return "FAIL";
}
'''+s[b:]
# Numeric/manual feeding commands must never fabricate a camera recognition.
pattern=r"    bench_v8::ai_species = '[CD]';\n    bench_v8::ai_species_ms = s.now_ms;\n"
s=re.sub(pattern,lambda m:m.group() if any(x in s[max(0,m.start()-90):m.start()] for x in ['"ai_cat"','"ai_dog"']) else '',s)
s=s.replace('  oled.print(bench_v8::stateText());','  oled.print("AI:"); oled.print(bench_v8::oledAiLineText(now));\n  oled.print(" "); oled.print(bench_v8::stateText());',1)
s=s.replace('return "CAT WAIT 5-20"','return "WAIT <=30cm"')
s=s.replace('void drawDistance(const char* label, float cm, int y) {',(r/'mcu_schedule.inc').read_text()+'\nvoid drawDistance(const char* label, float cm, int y) {')
s=s.replace('  if (!n) return;','  if (!n) return;\n  if (scheduled_feed_v1::command(line,s.now_ms)) return;',1)
s=s.replace('  bench_v8::tick(s, now);','  bench_v8::tick(s, now);\n  scheduled_feed_v1::tick();',1)
marker='  number(s.healthy ? s.grams : NAN);'
assert marker in s
s=s.replace(marker,marker+'\n  out.printf(",\\\"scheduled_protocol\\\":1,\\\"ai_oled\\\":\\\"%s\\\",\\\"inspect_required\\\":%s,\\\"demo_exited\\\":%s",bench_v8::oledAiLineText(s.now_ms),bench_v8::cat_inspect_required?"true":"false",bench_v8::demo_exited?"true":"false");',1)
(r/'esp32/esp32.ino').write_text(s)
print('Firmware: truthful CAT/DOG/FAIL OLED; scheduled idempotent commands with ACK/result.')
