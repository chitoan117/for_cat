"""Validate owner-created server config and immutable static release only.
No network, camera, API startup, Tailscale execution or secret output.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
from release_bundle import verify,digest

WEB_SHA='9c6410d7688d05325019be66c377761afc22170b6081d54dedfb5f04b66ba0ee'
EXPECTED={'API_HOST':'127.0.0.1','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK','ESP32_TRANSPORT':'MOCK',
          'SYSTEM_STATE_PROVIDER':'REAL','FORCAT_REMOTE_MODE':'TAILSCALE_SERVE','CORS_ORIGINS':'',
          'FORCAT_STREAM_ENABLED':'1','FORCAT_STREAM_SOURCE':'REAL','FORCAT_STREAM_PUBLISH':'1',
          'SCHEDULED_DRY_RUN_WORKER_ENABLED':'0'}
def inside(path,root):return path==root or root in path.parents
def private_file(value,bundle):
    p=Path(value)
    if not p.is_absolute() or p.is_symlink() or not p.is_file():raise ValueError('absolute regular server-only file required')
    p=p.resolve()
    if inside(p,bundle):raise ValueError('private config/token must be outside distributed release')
    if os.name=='posix' and stat.S_IMODE(p.stat().st_mode)&0o077:raise ValueError('private server file permissions must be0600')
    if p.stat().st_size>16384:raise ValueError('private file size bound')
    return p
def validate(config_file,bundle):
    bundle=Path(bundle).resolve();verify(bundle)
    config_path=private_file(config_file,bundle)
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(config,dict):raise ValueError('server config object required')
    for key,value in EXPECTED.items():
        if config.get(key)!=value:raise ValueError('unsafe or changed '+key)
    port=config.get('API_PORT','')
    if not isinstance(port,str) or not port.isdigit() or not 1024<=int(port)<=65535:raise ValueError('nonprivileged API port required')
    host=config.get('FORCAT_TAILSCALE_HOSTNAME','')
    if not isinstance(host,str) or len(host)>253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.ts\.net',host):
        raise ValueError('exact lower-case HTTPS tailnet hostname required')
    token_path=private_file(config.get('FORCAT_CAMERA_PRODUCER_TOKEN_FILE',''),bundle)
    token=token_path.read_bytes().strip()
    if not 32<=len(token)<=512 or any(c<33 or c>126 for c in token):raise ValueError('invalid server producer secret')
    access=private_file(config.get('FORCAT_ACCESS_POLICY_FILE',''),bundle)
    users=json.loads(access.read_text(encoding='utf-8')).get('users')
    if not isinstance(users,dict) or not 1<=len(users)<=64:raise ValueError('bounded access allowlist required')
    for user,roles in users.items():
        if not isinstance(user,str) or not user or not isinstance(roles,list) or not roles or not set(roles)<={'VIEW_CAMERA','FEED_MANUAL','CONTROL_SYSTEM'}:
            raise ValueError('invalid identity/scopes')
    if not any(set(roles)=={'VIEW_CAMERA'} for roles in users.values()):raise ValueError('separate VIEW_CAMERA-only identity required')
    web=bundle/'web_real'
    if digest(web/'main.dart.js')!=WEB_SHA:raise ValueError('reviewed REAL web artifact mismatch')
    marker=json.loads((web/'forcat_build.json').read_text(encoding='utf-8'))
    if marker.get('mode')!='REAL' or marker.get('base_href')!='/flutter/' or marker.get('actuator_execution') is not False:
        raise ValueError('static web deployment marker mismatch')
    # Avoid accidental packaging of the actual secret into any static asset.
    for asset in web.rglob('*'):
        if asset.is_file() and token in asset.read_bytes():raise ValueError('producer secret leaked into web artifact')
    return {'config_valid':True,'physical_pass':False,'real_stream':'NOT_VERIFIED','network_changed':False,
            'same_origin_required':'https://'+host,'providers_preserved':True,'viewer_only_identity_present':True,
            'web_sha256':WEB_SHA,'api_port':int(port),'camera_opened':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--bundle',required=True);args=p.parse_args()
    print(json.dumps(validate(args.config,args.bundle),indent=2))
if __name__=='__main__':main()
