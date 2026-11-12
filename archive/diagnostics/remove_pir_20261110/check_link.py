from pathlib import Path
import importlib.util,json,time
spec=importlib.util.spec_from_file_location('migration',Path(__file__).with_name('deploy_firmware.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=m.snapshot()
print(json.dumps({'age_seconds':round((time.monotonic()*1000-s['updated_monotonic_ms'])/1000,2),'device':s['device'],'last_received_at':s['last_received_at'],'fc_live':s['telemetry']['fc_live']}),flush=True)
