"""Private candidate config, strict fixed safe provider contract. No real-mode switch."""
import os
from pathlib import Path
import re
import secrets
from integrity import absolute,read,write_new

ENV={'API_HOST':'127.0.0.1','API_PORT':'8000','CAMERA_PROVIDER':'MOCK','AI_RUNTIME':'MOCK',
     'ESP32_TRANSPORT':'MOCK','SYSTEM_STATE_PROVIDER':'REAL','AI_SHADOW_MODE':'true','ESP32_BRIDGE_ENABLED':'1',
     'SCHEDULED_DRY_RUN_WORKER_ENABLED':'0','FORCAT_REMOTE_MODE':'TAILSCALE_SERVE','CORS_ORIGINS':'',
     'FORCAT_STREAM_ENABLED':'1','FORCAT_STREAM_SOURCE':'REAL','FORCAT_STREAM_PUBLISH':'1','FORCAT_JPEG_QUALITY':'70'}
def private(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>16384:raise ValueError('private regular bounded file required')
    if os.name=='posix' and p.stat().st_mode&0o077:raise ValueError('private file mode must be0600')
    return p
def validate(folder):
    folder=Path(folder).resolve();data=read(private(folder/'runtime.json'))
    if set(data)!=set(ENV)|{'FORCAT_TAILSCALE_HOSTNAME','FORCAT_ACCESS_POLICY_FILE','FORCAT_CAMERA_PRODUCER_TOKEN_FILE'}:raise ValueError('unexpected env keys')
    if any(data.get(k)!=v for k,v in ENV.items()):raise ValueError('provider/safety environment changed')
    host=data['FORCAT_TAILSCALE_HOSTNAME']
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.ts\.net',host) or '..' in host:raise ValueError('exact lowercase tailnet hostname required')
    for key,name in (('FORCAT_ACCESS_POLICY_FILE','access.json'),('FORCAT_CAMERA_PRODUCER_TOKEN_FILE','producer.token')):
        if Path(data[key]).resolve()!=folder/name:raise ValueError('private config must use its own files')
    token=private(folder/'producer.token').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',token):raise ValueError('producer token format')
    users=read(private(folder/'access.json')).get('users')
    if not isinstance(users,dict) or not users or any(not u or roles!=['VIEW_CAMERA'] for u,roles in users.items()):raise ValueError('initial candidate view-only allowlist required')
    return data
def prepare(folder,hostname,viewer):
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.ts\.net',hostname) or '..' in hostname or not viewer or '\n' in viewer:raise ValueError('real hostname/viewer required')
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False,mode=0o700)
    token=secrets.token_urlsafe(48)
    for name,data in [('runtime.json',{**ENV,'FORCAT_TAILSCALE_HOSTNAME':hostname,
        'FORCAT_ACCESS_POLICY_FILE':str(folder/'access.json'),'FORCAT_CAMERA_PRODUCER_TOKEN_FILE':str(folder/'producer.token')}),
        ('access.json',{'users':{viewer:['VIEW_CAMERA']}})]:
        write_new(folder/name,data);os.chmod(folder/name,0o600)
    with (folder/'producer.token').open('x') as f:f.write(token+'\n')
    os.chmod(folder/'producer.token',0o600);validate(folder)
    return {'prepared':str(folder),'secret_printed':False,'permissions':'VIEW_CAMERA_ONLY'}
def environment(folder,production):
    data=validate(folder);production=absolute(str(production))
    # Ignore inherited mode overrides, PYTHONPATH and application configuration.
    keep={k:v for k,v in os.environ.items() if k in ('PATH','HOME','LANG','LC_ALL','LD_LIBRARY_PATH','CUDA_VISIBLE_DEVICES')}
    return {**keep,**data,'DATABASE_PATH':str(production/'jetson/data/events.db'),'PYTHONDONTWRITEBYTECODE':'1'}
