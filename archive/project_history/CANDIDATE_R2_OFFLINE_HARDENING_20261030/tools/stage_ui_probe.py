import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parent/'CANDIDATE_GCC75_R2_20261029/candidate/flutter/hardware_diagnostics_panel.dart'
target=ROOT/'candidate/flutter/test/baseline_panel.dart'
with target.open('xb') as f:f.write(source.read_bytes())
with (ROOT/'evidence/baseline_ui_source.json').open('x') as f:json.dump({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'copied_unchanged_for_probe_only':True},f,indent=2)
