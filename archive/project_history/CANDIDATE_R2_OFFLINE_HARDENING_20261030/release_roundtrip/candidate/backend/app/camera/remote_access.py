"""Trusted-loopback Tailscale Serve identity boundary; never a feed authority.

Serve strips incoming Tailscale identity headers and supplies the authenticated
tailnet identity. Backend must bind loopback with uvicorn proxy_headers=False.
Local privileged processes are inside the trusted-host boundary, not tailnet users.
"""
from dataclasses import dataclass, field
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

SCOPES = frozenset({'VIEW_CAMERA', 'FEED_MANUAL', 'CONTROL_SYSTEM'})
IDENTITY = 'tailscale-user-login'

def loopback(value):
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False

@dataclass(frozen=True)
class RemotePolicy:
    mode: str = 'DISABLED'
    hostname: str = ''
    users: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, env):
        mode = env.get('FORCAT_REMOTE_MODE', 'DISABLED')
        if mode not in ('DISABLED', 'LOCAL_DEMO', 'TAILSCALE_SERVE'):
            raise ValueError('invalid FORCAT_REMOTE_MODE')
        if mode == 'DISABLED':
            return cls()
        if env.get('API_HOST', '127.0.0.1') not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('camera-enabled API must bind loopback')
        if env.get('CORS_ORIGINS', ''):
            raise ValueError('camera uses same-origin HTTPS; CORS must remain empty')
        if mode == 'LOCAL_DEMO':
            return cls(mode=mode)
        hostname = env.get('FORCAT_TAILSCALE_HOSTNAME', '').lower()
        if not hostname.endswith('.ts.net') or '/' in hostname or ':' in hostname or len(hostname) > 253:
            raise ValueError('exact tailnet HTTPS hostname required')
        path = Path(env.get('FORCAT_ACCESS_POLICY_FILE', ''))
        if not path.is_file() or path.stat().st_size > 16384:
            raise ValueError('server-side access policy file required')
        data = json.loads(path.read_text(encoding='utf-8'))
        users = data.get('users') if isinstance(data, dict) else None
        if not isinstance(users, dict) or not 1 <= len(users) <= 64:
            raise ValueError('explicit bounded user allowlist required')
        for user, scopes in users.items():
            if not isinstance(user, str) or not user or not isinstance(scopes, list) or not set(scopes) <= SCOPES:
                raise ValueError('invalid user scopes')
        return cls(mode=mode, hostname=hostname, users=users)

    def allowed(self, scope, required):
        peer = (scope.get('client') or ('', 0))[0]
        if not loopback(peer):
            return False
        raw = scope.get('headers', [])
        names = [k.lower() for k, _ in raw]
        for key in (b'host', b'origin', b'x-forwarded-proto', IDENTITY.encode()):
            if names.count(key) > 1:
                return False
        headers = {k.decode('latin1').lower(): v.decode('latin1') for k, v in raw}
        host = headers.get('host', '')
        try:
            parsed = urlsplit('http://' + host)
            hostname = parsed.hostname
            port = parsed.port
            if not hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                return False
        except ValueError:
            return False
        if headers.get('sec-fetch-site') == 'cross-site':
            return False
        if self.mode == 'LOCAL_DEMO':
            if hostname not in ('localhost', '127.0.0.1', '::1') or required != 'VIEW_CAMERA':
                return False
            origin = headers.get('origin')
            return origin is None or origin in ('http://' + host, 'https://' + host)
        if self.mode != 'TAILSCALE_SERVE' or hostname.lower() != self.hostname:
            return False
        if port not in (None, 443) or headers.get('x-forwarded-proto') != 'https':
            return False
        if headers.get('origin') not in (None, 'https://' + self.hostname):
            return False
        user = headers.get(IDENTITY)
        return bool(user and required in self.users.get(user, []))

class CameraAccessMiddleware:
    def __init__(self, app, policy):
        self.app, self.policy = app, policy

    async def __call__(self, scope, receive, send):
        if scope['type'] not in ('http', 'websocket'):
            return await self.app(scope, receive, send)
        path = scope.get('path', '')
        # Internal producer authentication is independent, in its router. Serve
        # identity is deliberately insufficient to call internal producer APIs.
        internal = path.startswith('/internal/camera/')
        camera = path.startswith('/api/v1/camera/')
        if self.policy.mode == 'DISABLED' and any(k.lower() in (b'tailscale-user-login',b'x-forwarded-proto') for k,_ in scope.get('headers',[])):
            if scope['type']=='websocket':
                await send({'type':'websocket.close','code':4403});return
            return await JSONResponse({'detail':'remote profile not configured'},status_code=403)(scope,receive,send)
        enforce = camera or (self.policy.mode != 'DISABLED' and not internal)
        if enforce:
            method = scope.get('method', 'GET')
            required = 'VIEW_CAMERA'
            if method not in ('GET', 'HEAD', 'OPTIONS'):
                required = 'FEED_MANUAL' if path in ('/api/feed/preview', '/api/v1/feed/manual') else 'CONTROL_SYSTEM'
            if not self.policy.allowed(scope, required):
                if scope['type'] == 'websocket':
                    await send({'type': 'websocket.close', 'code': 4403})
                    return
                response = JSONResponse({'detail': 'access denied', 'required_scope': required}, status_code=403)
                return await response(scope, receive, send)
        return await self.app(scope, receive, send)
