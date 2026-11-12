from pathlib import Path
r=Path(__file__).parent
p=r/'esp32/esp32.ino'
s=p.read_text(encoding='utf-8')
marker='void command(char* line, const Sample& s) {'
code='''// Exact historical UNO reference; only imported by an explicit cal_uno command.
// Normal boot continues to prefer the physically calibrated ESP32 NVS record.
bool restoreUnoScale(uint32_t now) {
  if (bench_cal != BenchCal::Idle || bench_v8::busy() || pwm.moving()
      || pcb_levels::running || !hx.raw.valid
      || uint32_t(now-hx.raw.sampled_at_ms)>1000u) {
    reply(0,false,"UNO_CAL_BLOCKED_STOP_OUTPUTS_AND_REQUIRE_FRESH_HX_RAW");
    return false;
  }
  m4::ScaleCalibration c;
  c.tared=true; c.calibrated=true;
  c.tare_counts=-668483.0;
  c.grams_per_count=1.0/-1064.4473;
  if (!c.valid()) return false;
  auto next=bench_record;
  next.hx711=c;
  if (!bench_nvs.save(next)) {
    reply(0,false,"UNO_CAL_NVS_SAVE_FAILED_KEEP_CURRENT"); return false;
  }
  bench_record=next;
  hx.applyCalibration(c);
  calibration_source="UNO_REFERENCE_EXPLICIT_IMPORT";
  calibration_load="SAVED";
  reply(0,true,"UNO_CAL_IMPORTED_CHECK_EMPTY_AND_KNOWN_38G_USE_t_TO_REZERO");
  return true;
}

'''
assert marker in s and 'bool restoreUnoScale(' not in s
s=s.replace(marker,code+marker)
# Route after whitespace normalization; changing reference cannot start a motor.
marker='  if (!n) return;'
s=s.replace(marker,marker+'''
  if (!std::strcmp(line,"cal_uno")) {
    restoreUnoScale(s.now_ms); return;
  }
  if (!std::strcmp(line,"servo_uno")) {
    if (bench_v8::busy() || pwm.moving() || bench_cal!=BenchCal::Idle) {
      reply(0,false,"SERVO_UNO_BLOCKED_WHILE_BUSY"); return;
    }
    bench_v8::open_ms=1100;
    bench_v8::close_ms=900;
    reply(0,true,"SERVO_UNO_RESTORED_1400us_1100ms_1600us_900ms_STOP1500_FINE170");
    return;
  }
''',1)
s=s.replace('if (!std::strcmp(line, "t")) {','if (!std::strcmp(line, "t") || !std::strcmp(line, "T")) {')
s=s.replace('"TUNE: open_ms', '"UNO: servo_uno restores tested timings; cal_uno explicitly imports historical scale; t/T rezero\\n"\n      "TUNE: open_ms')
p.write_text(s,encoding='utf-8')
print('Updated candidate with explicit reference restore and UNO uppercase tare compatibility.')
