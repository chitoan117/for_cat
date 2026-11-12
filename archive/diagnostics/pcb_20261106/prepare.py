from pathlib import Path
import shutil
r=Path(__file__).parent
src=Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino')
shutil.copy2(src,r/'esp32.before.ino')
s=src.read_text(encoding='utf-8')
s=s.replace('jsn_food','bowl_d1').replace('jsn_water','tank_d2')
s=s.replace('JSN_WATER_ECHO = 10','D2_WATER_ECHO = 19')
s=s.replace('GPIO10 is JSN water ECHO input, NOT a separate water-input output.', 'PCB D2 ECHO: J3_20 = GPIO19; use USB-UART, not native USB pins19/20.')
s=s.replace('CAT_MAX_CM = 20.0f','CAT_MAX_CM = 30.0f').replace('<=20cm','<=30cm').replace('5..20cm','5..30cm')
s=s.replace('{{18,true},{10,true}', '{{18,true},{19,true}')
s=s.replace('2.0f, 450.0f','2.0f, 400.0f')
s=s.replace('digitalRead(10)', 'digitalRead(19)')
s=s.replace('HC2 16/17; JSN FOOD 14/15; JSN WATER 18/10.', 'E2 FOOD 16/17; D1 BOWL 14/15; D2 TANK 18/19.')
s=s.replace('m4::Ultrasonic hc2(pins);      // HC-SR04 #2','m4::Ultrasonic hc2(pins);      // PCB E2 food reservoir')
s=s.replace('// JSN #1 - food bin distance','// PCB HC-SR04 D1 drinking bowl')
s=s.replace('// JSN #2 - water surface distance','// PCB HC-SR04 D2 water reservoir')
s=s.replace('NO water pump automatic control; NEVER move servo on boot.', 'D1/D2 calibrated water control; pump disabled until explicit configuration; never move servo on boot.')
start=s.index('float currentWaterPercent(uint32_t now) {')
end=s.index('\nbool beginAllSensors()',start)
levels='''// New PCB geometry has its own NVS namespace; never reuse old sensor geometry.
namespace pcb_levels {
m4::LevelCalibration food{}, bowl{}, tank{};
Preferences prefs;
bool storage = false;
float target = NAN;
bool enabled = false, running = false, fault = false;
uint32_t started = 0, low_stamp = 0;
unsigned low_hits = 0;
const char* reason = "DISABLED";
constexpr uint32_t FRESH_MS = 1200, MAX_RUN_MS = 30000;

float percent(const m4::Ultrasonic& u, const m4::LevelCalibration& g, uint32_t now) {
  if (!sensors_enabled || !g.valid() || !u.raw.valid || !u.filtered.valid
      || uint32_t(now-u.raw.sampled_at_ms)>FRESH_MS
      || uint32_t(now-u.filtered.sampled_at_ms)>FRESH_MS) return NAN;
  float p=100.0f*(g.empty_cm-u.filtered.value)/(g.empty_cm-g.full_cm);
  return p<0 ? 0 : (p>100 ? 100 : p);
}
void off(const char* why) {
  digitalWrite(current_hardware::PUMP_CONTROL, LOW); // PCB PC817 LED HIGH -> PMOS ON.
  running=false; low_hits=0; reason=why;
}
void disable() { enabled=false; off("DISABLED"); }
void load() {
  digitalWrite(current_hardware::PUMP_CONTROL,LOW);
  pinMode(current_hardware::PUMP_CONTROL,OUTPUT);
  storage=prefs.begin("fc_pcb_v1",false);
  if (!storage) return;
  m4::LevelCalibration* gs[]={&food,&bowl,&tank};
  const char* keys[]={"E2","D1","D2"};
  for (int i=0;i<3;++i) {
    float v[2];
    if (prefs.getBytesLength(keys[i])==sizeof(v) && prefs.getBytes(keys[i],v,sizeof(v))==sizeof(v))
      *gs[i]={true,v[0],v[1]};
  }
  target=prefs.getFloat("target",NAN);
  // Deliberately require pump_auto on after boot until physical commissioning.
}
void tick(uint32_t now) {
  if (!enabled || fault) { off(fault ? "TIMEOUT_LATCHED" : "DISABLED"); return; }
  float bp=percent(bowl_d1,bowl,now), tp=percent(tank_d2,tank,now);
  if (!std::isfinite(bp)||!std::isfinite(tp)||!std::isfinite(target)) { off("INVALID_LEVEL_OR_CALIBRATION"); return; }
  if (tp<=0.0f) { off("RESERVOIR_EMPTY"); return; }
  if (running) {
    if (uint32_t(now-started)>=MAX_RUN_MS) { fault=true; off("TIMEOUT_LATCHED"); return; }
    if (bp>=target) { off("TARGET_REACHED"); return; }
    return;
  }
  if (bp>=50.0f) { low_hits=0; reason="BOWL_SUFFICIENT"; return; }
  if (low_stamp==bowl_d1.raw.sampled_at_ms) return;
  low_stamp=bowl_d1.raw.sampled_at_ms;
  if (++low_hits<3) { reason="CONFIRMING_LOW_LEVEL"; return; }
  digitalWrite(current_hardware::PUMP_CONTROL,HIGH);
  running=true; started=now; reason="REFILLING";
}
bool command(const char* line, uint32_t now) {
  if (!std::strcmp(line,"pump_auto off")) { disable(); return true; }
  if (!std::strcmp(line,"pump_reset")) { disable(); fault=false; return true; }
  if (!std::strcmp(line,"pump_auto on")) {
    if (!fault && std::isfinite(target) && target>50 && target<=100
        && std::isfinite(percent(bowl_d1,bowl,now)) && std::isfinite(percent(tank_d2,tank,now))) {
      enabled=true; reason="ARMED";
    } else protocolSerial().print("PUMP BLOCKED: configure valid D1/D2 geometry, target >50..100, and fresh readings.\\n");
    return true;
  }
  if (!std::strncmp(line,"pump_target ",12)) {
    float v=0; char extra;
    if (std::sscanf(line+12,"%f %c",&v,&extra)==1 && std::isfinite(v) && v>50 && v<=100) {
      disable(); target=v;
      bool saved=storage && prefs.putFloat("target",v)==sizeof(float);
      protocolSerial().printf("PUMP target %.1f%% %s; still disabled.\\n",double(v),saved?"SAVED":"RAM_ONLY");
    } else protocolSerial().print("INVALID pump_target: >50..100 percent required.\\n");
    return true;
  }
  if (!std::strncmp(line,"level_cal ",10)) {
    char id[3]={},extra; float full=0,empty=0;
    if (std::sscanf(line+10,"%2s %f %f %c",id,&full,&empty,&extra)!=3
        || !std::isfinite(full)||!std::isfinite(empty)||full<2||empty>400||empty-full<0.5f) {
      protocolSerial().print("INVALID level_cal E2|D1|D2 full_cm empty_cm (2..400, span>=0.5).\\n"); return true;
    }
    m4::LevelCalibration* g=!std::strcmp(id,"E2")?&food:!std::strcmp(id,"D1")?&bowl:!std::strcmp(id,"D2")?&tank:nullptr;
    if (!g) { protocolSerial().print("UNKNOWN PCB sensor ID.\\n"); return true; }
    disable(); *g={true,full,empty}; float v[]={full,empty};
    bool saved=storage && prefs.putBytes(id,v,sizeof(v))==sizeof(v);
    protocolSerial().printf("LEVEL %s %.2f..%.2fcm %s\\n",id,double(full),double(empty),saved?"SAVED":"RAM_ONLY");
    return true;
  }
  return false;
}
}
float currentWaterPercent(uint32_t now) {
  return pcb_levels::percent(bowl_d1,pcb_levels::bowl,now);
}
'''
s=s[:start]+levels+s[end:]
s=s.replace('void command(char* line, const Sample& s) {','void command(char* line, const Sample& s) {\n  if (pcb_levels::command(line,s.now_ms)) return;\n  if (!std::strcmp(line,"0") || !std::strcmp(line,"stop") || !std::strcmp(line,"STOP") || !std::strcmp(line,"sensors_off")) pcb_levels::disable();')
s=s.replace('void setup() {','void setup() {\n  pcb_levels::load();',1)
s=s.replace('  tickButton(now);','  pcb_levels::tick(now);\n  tickButton(now);',1)
# Keep legacy UART distance keys for old clients; add unambiguous PCB metadata.
marker='  out.print(",\\\"water_level_percent\\\":");'
assert marker in s
s=s.replace(marker,'''  out.print(",\\\"pcb_profile\\\":\\\"HCSR04_E1_E2_D1_D2_V1\\\",\\\"food_reservoir_percent\\\":");
  number(pcb_levels::percent(hc2,pcb_levels::food,s.now_ms));
  out.print(",\\\"water_reservoir_percent\\\":");
  number(pcb_levels::percent(tank_d2,pcb_levels::tank,s.now_ms));
  out.printf(",\\\"pump_enabled\\\":%s,\\\"pump_running\\\":%s,\\\"pump_fault\\\":%s,\\\"pump_reason\\\":\\\"%s\\\",\\\"pump_target_percent\\\":",
    pcb_levels::enabled?"true":"false",pcb_levels::running?"true":"false",pcb_levels::fault?"true":"false",pcb_levels::reason);
  number(pcb_levels::target);
'''+marker)
# Old water_full/empty calibrates old D2 record; explicitly refuse this obsolete interface.
s=s.replace('    stageWaterCalibration(!std::strcmp(line, "water_full"), s.now_ms);','    reply(0,false,"USE_level_cal_D1_OR_D2_full_cm_empty_cm_FOR_NEW_PCB");')
s=s.replace('"JSN FOOD:"','"D1 BOWL: "').replace('"JSN H2O: "','"D2 TANK: "').replace('"HC2 AUX: "','"E2 FOOD: "')
s=s.replace('"SENSORS: sensors_on', '"PCB: level_cal E2|D1|D2 full_cm empty_cm; pump_target percent; pump_auto on|off; pump_reset\\n"\n      "SENSORS: sensors_on')
# Replace stale pin help without rewriting historical internal legacy controller.
s=s.replace('JSN WATER uses TRIG18 ECHO10','D2 TANK uses TRIG18 ECHO19').replace('18/10','18/19')
p=r/'esp32'; p.mkdir(exist_ok=True)
(p/'esp32.ino').write_text(s,encoding='utf-8')
print('Prepared',p/'esp32.ino')
