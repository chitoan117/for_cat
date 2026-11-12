"""Existing empty-manual-feed body contract, as transparent ASGI middleware.

BaseHTTPMiddleware response wrapping is intentionally avoided for infinite video.
The feeding validation/status codes themselves are unchanged.
"""
from starlette.responses import JSONResponse

class EmptyFeedBodyMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('method')!='POST' or scope.get('path')!='/api/v1/feed/manual':
            return await self.app(scope,receive,send)
        headers={k.lower():v for k,v in scope.get('headers',[])}
        length=headers.get(b'content-length')
        if length is not None:
            try:
                parsed=int(length)
                if parsed<0:raise ValueError('negative')
            except ValueError:
                return await JSONResponse({'detail':'invalid Content-Length'},status_code=400)(scope,receive,send)
            if parsed>0:
                return await JSONResponse({'detail':'feed request body not supported'},status_code=413)(scope,receive,send)
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            if message.get('body'):
                return await JSONResponse({'detail':'feed request body not supported'},status_code=413)(scope,receive,send)
            if not message.get('more_body',False):break
        first=True
        async def empty_receive():
            nonlocal first
            if first:first=False;return {'type':'http.request','body':b'','more_body':False}
            return await receive()
        return await self.app(scope,empty_receive,send)
