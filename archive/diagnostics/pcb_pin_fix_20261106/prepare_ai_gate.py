from pathlib import Path
import shutil
r=Path('D:/Agent_Cat/diagnostics/ai_gate_20261106');r.mkdir(exist_ok=True)
base=Path('D:/Agent_Cat/diagnostics/pcb_20261106/fc_live_bridge.before.py')
shutil.copy2(base,r/'fc_live_bridge.before.py');s=base.read_text()
s=s.replace('        self.cat_consecutive = 0\n        self.active_food_cmd', '''        self.cat_consecutive = 0
        self.dog_candidate_stamp = None
        self.dog_candidate_frames = 0
        self.dog_candidate_started_mono = 0.0
        self.active_food_cmd''',1)
needle='''            self.cat_consecutive = 0
            return

        cls = ai.get('classification')'''
assert needle in s
s=s.replace(needle,'''            self.cat_consecutive = 0
            self.dog_candidate_stamp = None
            self.dog_candidate_frames = 0
            self.dog_candidate_started_mono = 0.0
            return

        cls = ai.get('classification')''',1)
needle="        if cls == 'DOG' and conf >= 0.40:"
assert needle in s
s=s.replace(needle,'''        # A single flickering DOG label must not abort an accepted CAT motion.
        # Confirm distinct, fresh AI observations, rather than polling one frame.
        dog_signal = cls == 'DOG' and conf >= 0.70
        if not dog_signal:
            self.dog_candidate_stamp = None
            self.dog_candidate_frames = 0
            self.dog_candidate_started_mono = 0.0
        elif stamp != self.dog_candidate_stamp:
            if self.dog_candidate_frames == 0:
                self.dog_candidate_started_mono = now_mono
            self.dog_candidate_stamp = stamp
            self.dog_candidate_frames += 1
        dog_confirmed = (
            dog_signal and self.dog_candidate_frames >= 3
            and (now_mono - self.dog_candidate_started_mono) >= 1.0
        )

        if dog_confirmed:''',1)
(r/'fc_live_bridge.py').write_text(s)
print('Prepared bridge-only DOG confirmation; no firmware/UI/35g/30cm changes.')
