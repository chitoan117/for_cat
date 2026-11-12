"""Owner-run read-only inventory; no camera open, UART open or service changes.
Requires Python3.8+ (use the integration3.11 venv, not Jetson system3.6).
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ENGINE_SHA='48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb'
SERVICES=('for-cat-ai.service','for-cat-api.service','for-cat-esp32-bridge.service')
def query(command):
    try:
        p=subprocess.run(command,capture_output=True,text=True,timeout=15)
        return {'argv':command,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except (OSError,subprocess.TimeoutExpired) as e:return {'argv':command,'error':str(e)}
def inspect(root):
    root=Path(root).resolve();engine=root/'models/tensorrt/yolov8n_320_fp16.engine'
    # Explicit allowlist: these commands only inspect dependencies/ownership.
    queries=[['g++','--version']]+[['pkg-config','--modversion',p] for p in ('opencv4','json-c','sqlite3')]
    queries += [['systemctl','is-active',s] for s in SERVICES]
    queries += [['fuser','/dev/video0'],['v4l2-ctl','--list-devices']]
    checks=[query(q) for q in queries]
    engine_hash=hashlib.sha256(engine.read_bytes()).hexdigest() if engine.is_file() else None
    trt=any(Path(p).is_file() for p in ('/usr/include/aarch64-linux-gnu/NvInfer.h','/usr/include/NvInfer.h'))
    cuda=Path('/usr/local/cuda-10.2/include/cuda_runtime_api.h').is_file()
    deps=all(q.get('returncode')==0 for q in checks[:4])
    return {'kind':'JETSON_READ_ONLY_PREFLIGHT','architecture':platform.machine(),'python':platform.python_version(),
            'engine_sha256':engine_hash,'engine_matches_historical':engine_hash==ENGINE_SHA,'tensorrt_headers':trt,
            'cuda_10_2_headers':cuda,'queries':checks,'camera_opened':False,'production_changed':False,
            'build_preconditions':platform.machine()=='aarch64' and deps and trt and cuda and engine_hash==ENGINE_SHA,
            'arm64_build':'NOT_VERIFIED','physical_pass':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--production-root',required=True);args=p.parse_args()
    print(json.dumps(inspect(args.production_root),indent=2))
if __name__=='__main__':main()
