from pathlib import Path
import hashlib
import difflib

root = Path(__file__).parent
source = Path(r'D:\CODE_TEST_LOADCELL_CHUAN\esp32\esp32.ino')
original = source.read_text(encoding='utf-8-sig')
backup = root / 'esp32.original.ino'
if backup.exists():
    raise SystemExit('Backup already exists; do not overwrite')
backup.write_bytes(source.read_bytes())
text = original

def replace(old, new):
    global text
    if text.count(old) != 1:
        raise ValueError(f'Expected one occurrence: {old[:90]!r}')
    text = text.replace(old, new)

replace('constexpr int PIN_CLOSE_LIMIT = 47;',
        'constexpr bool USE_CLOSE_LIMIT_SWITCH = false; // Timed closure selected by owner.\nconstexpr int PIN_CLOSE_LIMIT = 47;')
replace('void tickLimitSwitch(uint32_t now) {',
        'void tickLimitSwitch(uint32_t now) {\n  if (!USE_CLOSE_LIMIT_SWITCH) return;')
replace('constexpr uint32_t SERVO_DIAG_MS = 4000; // direct test runs until limit switch or max 4s\n', '')
replace('uint16_t close_ms = 4000; // Failsafe ceiling while closing (4s); stops immediately at V-153-1C25 limit switch (GPIO47)',
        'uint16_t close_ms = 4000; // Timed close duration; inherited value, requires mechanical timing check.')
replace('if (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW) {',
        'if (USE_CLOSE_LIMIT_SWITCH && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW)) {')
replace('-> rotating until GPIO47 limit switch hit (max %ums).',
        '-> TIMED rotation for %ums; physical closure not measured.')
replace('(unsigned)SERVO_DIAG_MS);', '(unsigned)(opening ? open_ms : close_ms));')
replace('const bool hit_close_limit = (feed_stage == FeedStage::DIAG_CLOSE) && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW);\n    if (hit_close_limit || uint32_t(now - phase_at) >= SERVO_DIAG_MS) {',
        'const bool hit_close_limit = USE_CLOSE_LIMIT_SWITCH && (feed_stage == FeedStage::DIAG_CLOSE) && (limit_closed || digitalRead(PIN_CLOSE_LIMIT) == LOW);\n    const uint32_t duration = feed_stage == FeedStage::DIAG_OPEN ? open_ms : close_ms;\n    if (hit_close_limit || uint32_t(now - phase_at) >= duration) {')
replace('SERVO TEST FINISHED. Re-arm for another isolated test.',
        'SERVO TIMED TEST FINISHED; physical position not measured. Re-arm for another isolated test.')
replace('const bool hit_limit = limit_closed || (digitalRead(PIN_CLOSE_LIMIT) == LOW);',
        'const bool hit_limit = USE_CLOSE_LIMIT_SWITCH && (limit_closed || (digitalRead(PIN_CLOSE_LIMIT) == LOW));')
replace('"CLOSING: %lums / %ums | GPIO47=%s\\n",\n        (unsigned long)close_elapsed, (unsigned)close_ms,\n        (digitalRead(PIN_CLOSE_LIMIT) == LOW) ? "LOW(CHAM CONG TAC)" : "HIGH(HO)");',
        '"CLOSING TIMED: %lums / %ums | limit switch DISABLED\\n",\n        (unsigned long)close_elapsed, (unsigned)close_ms);')
replace('physical_closed_verified = hit_limit;\n      cat_inspect_required = false;',
        'physical_closed_verified = hit_limit;\n      cat_inspect_required = !close_on_weight && !hit_limit;')
replace('} else {\n        protocolSerial().printf(\n          "CAT SERVO STOPPED BY SAFETY TIMEOUT',
        '} else if (!USE_CLOSE_LIMIT_SWITCH) {\n        protocolSerial().printf(\n          "CAT SERVO STOPPED AFTER TIMED CLOSE %ums (delta %.2fg); physical closure not measured.\\n",\n          (unsigned)close_ms, double(last_delta_g));\n      } else {\n        protocolSerial().printf(\n          "CAT SERVO STOPPED BY SAFETY TIMEOUT')
replace('digitalRead(PIN_CLOSE_LIMIT) == LOW ? "LOW" : "HIGH",',
        'USE_CLOSE_LIMIT_SWITCH ? (digitalRead(PIN_CLOSE_LIMIT) == LOW ? "LOW" : "HIGH") : "DISABLED",')
replace('"\\\"limit_switch_gpio\\\":%d,\\\"limit_switch_closed\\\":%s,"',
        '"\\\"closure_mode\\\":\\\"%s\\\",\\\"limit_switch_enabled\\\":%s,"\n    "\\\"limit_switch_gpio\\\":%s,\\\"limit_switch_closed\\\":%s,"')
replace('    PIN_CLOSE_LIMIT,\n    limit_closed ? "true" : "false",\n    (limit_closed || physical_closed_verified) ? "true" : "false"',
        '    USE_CLOSE_LIMIT_SWITCH ? "LIMIT_SWITCH" : "TIMED",\n    USE_CLOSE_LIMIT_SWITCH ? "true" : "false",\n    USE_CLOSE_LIMIT_SWITCH ? "47" : "null",\n    USE_CLOSE_LIMIT_SWITCH ? (limit_closed ? "true" : "false") : "null",\n    USE_CLOSE_LIMIT_SWITCH ? ((limit_closed || physical_closed_verified) ? "true" : "false") : "null"')
replace('  if (!std::strcmp(line, "limit")) {',
        '  if (!std::strcmp(line, "limit")) {\n    if (!USE_CLOSE_LIMIT_SWITCH) {\n      protocolSerial().print("LIMIT SWITCH DISABLED: closing uses close_ms; physical position UNKNOWN.\\n");\n      return;\n    }')
replace('  pinMode(PIN_CLOSE_LIMIT, INPUT_PULLUP);\n  limit_raw_old = limit_closed = (digitalRead(PIN_CLOSE_LIMIT) == LOW);\n  physical_closed_verified = limit_closed;',
        '  if (USE_CLOSE_LIMIT_SWITCH) {\n    pinMode(PIN_CLOSE_LIMIT, INPUT_PULLUP);\n    limit_raw_old = limit_closed = (digitalRead(PIN_CLOSE_LIMIT) == LOW);\n    physical_closed_verified = limit_closed;\n  }')
replace('"TUNE: open_ms 550, close_ms 550 (100..1500ms), stop\\n"',
        '"TUNE: open_ms 550, close_ms 4000 (100..5000ms), idle only; stop\\n"\n      "CLOSURE: TIMED; GPIO47 disabled; physical position UNKNOWN.\\n"')
replace('? "SERVO OPEN DURATION UPDATED\\n" : "Invalid ms: choose 100..1500, idle only.\\n"',
        '? "SERVO OPEN DURATION UPDATED\\n" : "Invalid ms: choose 100..5000, idle only.\\n"')
replace('? "SERVO CLOSE DURATION UPDATED\\n" : "Invalid ms: choose 100..1500, idle only.\\n"',
        '? "SERVO CLOSE DURATION UPDATED\\n" : "Invalid ms: choose 100..5000, idle only.\\n"')
replace('"Servo GPIO6, buzzer GPIO1. Timed close cannot verify actual closed!\\n"',
        '"Servo GPIO6, buzzer GPIO2. TIMED CLOSE; GPIO47 disabled; physical position UNKNOWN.\\n"')
replace('//   open_ms 550 / close_ms 550 for supervised timing calibration.',
        '//   open_ms 550 / close_ms 4000; timed closure selected, GPIO47 disabled.')
out = root / 'esp32' / 'esp32.ino'
out.parent.mkdir(exist_ok=True)
out.write_text(text, encoding='utf-8', newline='\r\n')
(root / 'change.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(source),tofile=str(out))),encoding='utf-8')
print('Original SHA256:', hashlib.sha256(source.read_bytes()).hexdigest())
print('Candidate SHA256:', hashlib.sha256(out.read_bytes()).hexdigest())
print('Candidate:', out)
