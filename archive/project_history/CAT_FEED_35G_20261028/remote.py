"""Send an explicitly selected script to Jetson; preserve per-call output locally."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
script = Path(sys.argv[1]).resolve()
if script.parent != ROOT:
    raise ValueError("script must belong to this milestone")
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
ssh = ["ssh", "-6", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=yes",
       "-o", "HostKeyAlias=server-jetson.local", "-i", r"C:\Users\chito\.ssh\opencode_jetson",
       "toan@fe80::2f03:e65b:a064:b574%13", "/usr/bin/python3 -"]
p = subprocess.run(ssh, input=script.read_bytes(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
(ROOT / (stamp + "_" + script.stem + ".stdout.log")).write_bytes(p.stdout)
(ROOT / (stamp + "_" + script.stem + ".stderr.log")).write_bytes(p.stderr)
sys.stdout.buffer.write(p.stdout)
sys.stderr.buffer.write(p.stderr)
raise SystemExit(p.returncode)
