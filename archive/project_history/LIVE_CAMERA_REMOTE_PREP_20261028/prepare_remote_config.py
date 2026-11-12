"""Prepare NEW server-only files. Does not install/login/run Tailscale."""
import argparse
import json
import os
from pathlib import Path
import secrets

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--hostname',required=True)
    p.add_argument('--viewer',required=True);p.add_argument('--operator');args=p.parse_args()
    if not args.hostname.endswith('.ts.net') or any(c in args.hostname for c in '/:@\n\r'):
        p.error('use the actual exact HTTPS tailnet hostname')
    if any('REPLACE' in v or 'EXAMPLE' in v.upper() for v in (args.hostname,args.viewer,args.operator or '')):
        p.error('replace example identities before preparing live configuration')
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    users={args.viewer:['VIEW_CAMERA']}
    if args.operator:
        if args.operator==args.viewer:p.error('viewer and operator must be distinct for least privilege')
        users[args.operator]=['VIEW_CAMERA','FEED_MANUAL']
    for name,text in [('access.json',json.dumps({'users':users},indent=2)+'\n'),('producer.token',secrets.token_urlsafe(48)+'\n')]:
        fd=os.open(out/name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as file:file.write(text)
    env={'API_HOST':'127.0.0.1','API_PORT':'8000','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','ESP32_TRANSPORT':'MOCK',
         'ESP32_BRIDGE_ENABLED':'1','SYSTEM_STATE_PROVIDER':'REAL','SCHEDULED_DRY_RUN_WORKER_ENABLED':'0',
         'FORCAT_REMOTE_MODE':'TAILSCALE_SERVE','FORCAT_TAILSCALE_HOSTNAME':args.hostname,
         'FORCAT_ACCESS_POLICY_FILE':str(out/'access.json'),'FORCAT_STREAM_ENABLED':'1','FORCAT_STREAM_SOURCE':'REAL',
         'FORCAT_CAMERA_PRODUCER_TOKEN_FILE':str(out/'producer.token'),'FORCAT_STREAM_PUBLISH':'1','FORCAT_JPEG_QUALITY':'70','CORS_ORIGINS':''}
    # JSON avoids executing untrusted strings through a shell .env parser.
    (out/'server-env.json').write_text(json.dumps(env,indent=2)+'\n',encoding='utf-8')
    print('Prepared server-only configuration in '+str(out)+'; secret contents not printed. No Tailscale command executed.')
if __name__=='__main__':main()
