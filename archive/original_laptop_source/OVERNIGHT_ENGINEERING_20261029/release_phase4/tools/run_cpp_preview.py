"""Future operator launch only. Default prints a plan and opens no camera."""
import argparse
import json
import os
from pathlib import Path
import subprocess

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--repo',required=True)
    p.add_argument('--binary',required=True);p.add_argument('--roi-config',default='-');p.add_argument('--device',default='/dev/video0')
    p.add_argument('--execute',action='store_true');args=p.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8'))
    if config.get('API_HOST')!='127.0.0.1' or config.get('FORCAT_STREAM_SOURCE')!='REAL':
        raise ValueError('REAL loopback producer profile required')
    root=Path(args.repo).resolve();command=[str(Path(args.binary).resolve()),str(root/'jetson/data/events.db'),args.roi_config,args.device]
    if not args.execute:
        print('PLAN ONLY, no camera opened: '+json.dumps(command));return
    if os.name!='posix':raise ValueError('real C++ producer is for Jetson/Linux; Windows uses synthetic_video.py')
    owned=subprocess.run(['fuser',args.device],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if owned.returncode!=1:raise RuntimeError('camera busy or ownership cannot be established; do not launch a second capture')
    env={**os.environ,**config}
    os.execve(command[0],command,env)
if __name__=='__main__':main()
