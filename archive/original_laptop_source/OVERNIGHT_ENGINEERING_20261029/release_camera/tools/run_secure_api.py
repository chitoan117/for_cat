"""Operator launch helper: load server JSON config, loopback only, no proxy trust."""
import argparse
import json
import os
from pathlib import Path
import sys
import uvicorn

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--repo',required=True)
    p.add_argument('--flutter-web-dir',required=True);args=p.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8'))
    if config.get('API_HOST')!='127.0.0.1' or config.get('FORCAT_REMOTE_MODE')!='TAILSCALE_SERVE':
        raise ValueError('secure loopback-only Tailscale profile required')
    os.environ.update(config)
    root=Path(args.repo).resolve();sys.path.insert(0,str(root/'jetson'))
    os.environ['DATABASE_PATH']=str(root/'jetson/data/events.db')
    os.environ['FORCAT_FLUTTER_WEB_DIR']=str(Path(args.flutter_web_dir).resolve())
    from app.main import create_app
    app=create_app()
    uvicorn.run(app,host='127.0.0.1',port=int(config['API_PORT']),proxy_headers=False,workers=1,timeout_graceful_shutdown=5)
if __name__=='__main__':main()
