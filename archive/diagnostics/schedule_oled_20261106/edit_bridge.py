from pathlib import Path
r=Path(__file__).parent;s=(r/'before/fc_live_bridge.py').read_text()
s=s.replace('class BridgeRunner:',(r/'delivery.inc.py').read_text()+'\nclass BridgeRunner:',1)
s=s.replace('        self._init_db()','        self._init_db()\n        self.status_received_mono = float("-inf")\n        self.scheduled_delivery = ScheduledDelivery(self)',1)
s=s.replace('        self.last_status = msg','        self.last_status = msg\n        self.status_received_mono = time.monotonic()',1)
# Separate recognition display from DOG actuator confirmation and from feed state.
marker='    def check_commands_and_ai(self, ser: serial.Serial):'
s=s.replace(marker,'''    def publish_ai_display(self, ser, cls, confidence):
        label = cls if cls in ('CAT','DOG') and confidence >= 0.40 else 'NONE'
        if label != self.last_ai_oled or time.monotonic()-self.last_ai_oled_mono >= 1.5:
            self.last_ai_oled=label
            self.last_ai_oled_mono=time.monotonic()
            self.send_cmd(ser, {'CAT':'ai_cat','DOG':'ai_dog','NONE':'ai_none'}[label], 'OLED_RECOGNITION_'+label)

'''+marker)
s=s.replace('''                        decision = make_canonical_decision(req_id, req_body, 'DISPATCHED_TO_ESP32_35G')''','''                        if json.loads(req_body).get('source') == 'SCHEDULED':
                            continue
                        decision = make_canonical_decision(req_id, req_body, 'DISPATCHED_TO_ESP32_35G')''',1)
s=s.replace('        # 3. Check live AI state in ai_latest','''        try:
            self.scheduled_delivery.tick(ser)
        except sqlite3.Error as exc:
            print('[bridge] scheduled delivery retry:', exc, flush=True)

        # 3. Check live AI state in ai_latest''',1)
# Old startup code rewrote even legitimate ACK decisions as generic blocked.
s=s.replace("if dec.get('status') != 'DRY_RUN_BLOCKED' or dec.get('request_id') != req_id:","if dec.get('status') != 'DRY_RUN_BLOCKED' or dec.get('request_id') != req_id:")
s=s.replace('''            self.cat_consecutive = 0
            self.dog_candidate_stamp = None''','''            self.publish_ai_display(ser, 'NONE', 0.0)
            self.cat_consecutive = 0
            self.dog_candidate_stamp = None''',1)
s=s.replace("        # A single flickering DOG label", "        self.publish_ai_display(ser, cls, conf)\n\n        # A single flickering DOG label",1)
# Remove the older branch-specific display writes (unconfirmed DOG would otherwise be cleared).
a=s.index("            if self.last_ai_oled != 'DOG'");b=s.index('            if not dog_running',a);s=s[:a]+s[b:]
a=s.index("            if self.last_ai_oled != 'CAT'");b=s.index('            if (',a);s=s[:a]+s[b:]
a=s.index("            if self.last_ai_oled != 'NONE'");b=s.index('\n    def run_forever',a);s=s[:a]+s[b:]
s=s.replace("                                elif mtype == 'meal_preference':", "                                elif mtype in ('scheduled_ack','scheduled_result'):\n                                    self.scheduled_delivery.handle(msg)\n                                    self.log_event(mtype,msg)\n                                elif mtype == 'meal_preference':",1)
(r/'fc_live_bridge.py').write_text(s)
assert 'self.status_received_mono = time.monotonic()' in s
print('Prepared acknowledged scheduled delivery and independent AI OLED publication.')
