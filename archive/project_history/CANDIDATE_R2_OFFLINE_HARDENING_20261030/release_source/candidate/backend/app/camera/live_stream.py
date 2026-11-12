"""Read-only latest-JPEG fan-out. Never opens a webcam or writes food/device state."""
import asyncio
from collections import deque
import base64
from dataclasses import dataclass
import hmac
import json
import math
from pathlib import Path
import struct
import time

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import StreamingResponse

from app.camera.remote_access import loopback
from app.device_state import decode_cached_object

@dataclass(frozen=True)
class VideoSettings:
    enabled: bool = False
    source: str = 'REAL'
    max_viewers: int = 4
    max_jpeg_bytes: int = 524288
    stale_seconds: float = 2.0
    send_timeout_seconds: float = 5.0
    max_stream_seconds: float = 300.0
    producer_token: str = ''

    @classmethod
    def from_env(cls, env):
        flag = env.get('FORCAT_STREAM_ENABLED', '0')
        if flag not in ('0', '1'):
            raise ValueError('FORCAT_STREAM_ENABLED must be0 or1')
        if flag == '0':
            return cls()
        token_file = Path(env.get('FORCAT_CAMERA_PRODUCER_TOKEN_FILE', ''))
        if not token_file.is_file() or token_file.stat().st_size > 256:
            raise ValueError('private producer token file required')
        token = token_file.read_text(encoding='ascii').strip()
        if not 32 <= len(token) <= 128 or not all(c.isalnum() or c in '-_' for c in token):
            raise ValueError('invalid producer token')
        source = env.get('FORCAT_STREAM_SOURCE', 'REAL')
        viewers = int(env.get('FORCAT_CAMERA_MAX_VIEWERS', '4'))
        size = int(env.get('FORCAT_CAMERA_MAX_JPEG_BYTES', '524288'))
        if source not in ('REAL', 'SIMULATED') or not 1 <= viewers <= 16 or not 4096 <= size <= 1048576:
            raise ValueError('invalid video budget')
        return cls(enabled=True, source=source, max_viewers=viewers, max_jpeg_bytes=size, producer_token=token)

def jpeg_dimensions(data):
    if len(data) < 8 or data[:2] != b'\xff\xd8' or data[-2:] != b'\xff\xd9':
        raise ValueError('invalid JPEG envelope')
    at = 2
    while at + 4 <= len(data):
        if data[at] != 255:
            raise ValueError('invalid JPEG marker')
        while at < len(data) and data[at] == 255:
            at += 1
        if at >= len(data):
            break
        marker = data[at]; at += 1
        if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
            continue
        if at + 2 > len(data):
            break
        size = struct.unpack_from('>H', data, at)[0]
        if size < 2 or at + size > len(data):
            raise ValueError('invalid JPEG segment')
        if marker in (0xc0, 0xc1, 0xc2):
            if size < 8:
                raise ValueError('invalid JPEG SOF')
            height, width = struct.unpack_from('>HH', data, at + 3)
            return width, height
        if marker == 0xda:
            break
        at += size
    raise ValueError('JPEG dimensions unavailable')

def finite(value):
    return type(value) in (int, float) and math.isfinite(value)

def validate_meta(meta, data, settings, now_ms):
    if not isinstance(meta, dict) or len(json.dumps(meta)) > 4096:
        raise ValueError('metadata bound')
    if meta.get('source') != settings.source or meta.get('simulated') is not (settings.source == 'SIMULATED'):
        raise ValueError('REAL/SIMULATED source mismatch')
    epoch, frame_id = meta.get('producer_epoch'), meta.get('frame_id')
    if not isinstance(epoch, str) or not 1 <= len(epoch) <= 128 or type(frame_id) is not int or not 1 <= frame_id <= 2**63-1:
        raise ValueError('invalid frame identity')
    if type(meta.get('metadata_frame_id')) is not int or type(meta.get('overlay_frame_id')) is not int or meta.get('metadata_frame_id') != frame_id or meta.get('overlay_frame_id') != frame_id:
        raise ValueError('metadata/frame identity mismatch')
    captured, metadata_at = meta.get('captured_monotonic_ms'), meta.get('metadata_monotonic_ms')
    if not finite(captured) or not finite(metadata_at) or captured != metadata_at or not 0 <= now_ms-captured <= 1500:
        raise ValueError('stale or mismatched metadata timestamp')
    width, height = jpeg_dimensions(data)
    if type(meta.get('width')) is not int or type(meta.get('height')) is not int or (width, height) != (meta['width'], meta['height']):
        raise ValueError('JPEG/metadata dimensions mismatch')
    if not 2 <= width <= 1280 or not 2 <= height <= 960:
        raise ValueError('invalid preview dimensions')
    if meta.get('classification') not in ('CAT', 'DOG', 'NONE', 'UNKNOWN'):
        raise ValueError('invalid classification')
    confidence = meta.get('confidence')
    if meta['classification'] in ('CAT', 'DOG') and (not finite(confidence) or not 0 <= confidence <= 1):
        raise ValueError('invalid confidence')
    if meta['classification'] in ('NONE','UNKNOWN') and confidence is not None:
        raise ValueError('invalid NONE/UNKNOWN confidence')
    if meta.get('overlay_applied') is not True:
        raise ValueError('same-frame annotations required')
    boxes = meta.get('detections')
    if not isinstance(boxes, list) or len(boxes) > 8:
        raise ValueError('bbox bound')
    for box in boxes:
        if not isinstance(box, dict) or box.get('species') not in ('CAT', 'DOG'):
            raise ValueError('invalid bbox species')
        coords = box.get('bbox')
        if not isinstance(coords, list) or len(coords) != 4 or not all(finite(v) for v in coords):
            raise ValueError('invalid bbox coordinates')
        a,b,c,d = coords
        if not 0 <= a < c <= 1 or not 0 <= b < d <= 1:
            raise ValueError('bbox outside original normalized frame')
    if meta.get('roi_mode') not in ('FULL_FRAME', 'ROI_ENABLED'):
        raise ValueError('invalid ROI mode')
    roi = meta.get('food_roi')
    if meta['roi_mode']=='ROI_ENABLED' and roi is None and meta['classification']!='UNKNOWN':
        raise ValueError('uncalibrated ROI cannot claim a qualified scene')
    if meta['roi_mode'] == 'FULL_FRAME' and roi is not None:
        raise ValueError('FULL_FRAME must not pretend to show a tray ROI')
    if roi is not None:
        if not isinstance(roi, list) or len(roi) != 4 or not all(finite(v) for v in roi):
            raise ValueError('invalid ROI overlay')
        a,b,c,d=roi
        if not 0 <= a < c <= 1 or not 0 <= b < d <= 1:
            raise ValueError('invalid ROI bounds')
    return dict(meta)

class FrameHub:
    def __init__(self, settings=None, monotonic=time.monotonic):
        self.settings = settings or VideoSettings()
        self.clock = monotonic
        self.condition = asyncio.Condition()
        self.frame = None
        self.viewers = set()
        self.sequence = 0
        self.closed = False
        self.published = self.dropped = self.rejected = 0
        self.preview_until = 0.0
        self.producer_epoch = None
        self.last_frame_id = 0
        self.retired_epochs = deque(maxlen=16)

    def request_preview(self):
        self.preview_until = self.clock()+2.0

    def demand(self):
        return len(self.viewers)+(1 if self.preview_until>self.clock() else 0)

    def latest(self):
        if self.frame and self.clock()-self.frame[1]['captured_monotonic_ms']/1000 > self.settings.stale_seconds:
            self.frame = None
        return self.frame

    async def publish(self, data, meta):
        if not self.settings.enabled or self.closed or len(data) > self.settings.max_jpeg_bytes:
            raise ValueError('disabled/closed/oversized frame')
        meta = validate_meta(meta, data, self.settings, self.clock()*1000)
        epoch=meta['producer_epoch']
        if epoch in self.retired_epochs or (epoch==self.producer_epoch and meta['frame_id']<=self.last_frame_id):
            raise ValueError('old/duplicate producer frame (watermark retained across stale expiry)')
        old = self.latest()
        if old:
            old_meta = old[1]
            if meta['producer_epoch'] != old_meta['producer_epoch']:
                raise ValueError('another producer still has a fresh frame')
            if meta['frame_id'] <= old_meta['frame_id']:
                raise ValueError('old/duplicate frame')
            self.dropped += 1
        async with self.condition:
            if epoch!=self.producer_epoch:
                if self.producer_epoch:self.retired_epochs.append(self.producer_epoch)
                self.producer_epoch=epoch
            self.last_frame_id=meta['frame_id']
            self.sequence += 1
            self.frame = (bytes(data), meta, self.clock(), self.sequence)
            self.published += 1
            self.condition.notify_all()

    def acquire(self):
        if not self.latest():
            raise HTTPException(503, 'CAMERA_OFFLINE')
        if len(self.viewers) >= self.settings.max_viewers:
            raise HTTPException(429, 'viewer limit reached')
        token = object(); self.viewers.add(token)
        return token

    def release(self, token):
        self.viewers.discard(token)

    async def next_frame(self, previous):
        async with self.condition:
            if not self.closed and (not self.latest() or self.sequence == previous):
                try:
                    await asyncio.wait_for(self.condition.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
            return self.latest()

    async def close(self):
        async with self.condition:
            self.closed = True; self.frame = None
            self.viewers.clear();self.preview_until=0
            self.condition.notify_all()

    def status(self):
        frame = self.latest()
        meta = frame[1] if frame else None
        return {'status': 'CAMERA_ONLINE' if frame and not self.closed else 'CAMERA_OFFLINE',
                'source': self.settings.source, 'simulated': self.settings.source == 'SIMULATED',
                'viewers': len(self.viewers), 'max_viewers': self.settings.max_viewers,
                'frame_slots': 1, 'buffered_bytes': len(frame[0]) if frame else 0,
                'frame_id': meta['frame_id'] if meta else None, 'width': meta['width'] if meta else None,
                'producer_epoch':meta['producer_epoch'] if meta else None,
                'height': meta['height'] if meta else None,
                'frame_age_seconds': max(0, self.clock()-meta['captured_monotonic_ms']/1000) if meta else None,
                'annotations': 'BURNED_IN_SAME_FRAME_NOT_STATUS_OVERLAY',
                'stream_lease_seconds':self.settings.max_stream_seconds,
                'classification': meta['classification'] if meta else 'UNKNOWN',
                'confidence': meta.get('confidence') if meta else None,
                'published': self.published, 'replaced_frames': self.dropped, 'rejected_frames': self.rejected,
                'actuator_execution': False}

class MjpegResponse(StreamingResponse):
    def __init__(self, hub, token, max_frames=None):
        self.hub, self.token = hub, token
        async def frames():
            previous=0; sent=0; start=hub.clock()
            while not hub.closed and hub.clock()-start < hub.settings.max_stream_seconds:
                frame=await hub.next_frame(previous)
                if not frame:
                    break
                if frame[3]==previous:
                    continue
                previous=frame[3];sent+=1
                data,meta=frame[0],frame[1]
                yield (b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(data)).encode()+
                       b'\r\nX-Frame-Id: '+str(meta['frame_id']).encode()+b'\r\n\r\n'+data+b'\r\n')
                if max_frames is not None and sent>=max_frames:
                    break
            yield b'--frame--\r\n'
        super().__init__(frames(),media_type='multipart/x-mixed-replace; boundary=frame',headers={
            'Cache-Control':'no-store, private','X-Accel-Buffering':'no','X-Content-Type-Options':'nosniff',
            'Cross-Origin-Resource-Policy':'same-origin','X-Camera-Source':hub.settings.source,
            'Content-Security-Policy':"default-src 'none'; frame-ancestors 'self'"})

    async def stream_response(self, send):
        await asyncio.wait_for(send({'type':'http.response.start','status':self.status_code,'headers':self.raw_headers}),self.hub.settings.send_timeout_seconds)
        async for chunk in self.body_iterator:
            await asyncio.wait_for(send({'type':'http.response.body','body':chunk,'more_body':True}),self.hub.settings.send_timeout_seconds)
        await asyncio.wait_for(send({'type':'http.response.body','body':b'','more_body':False}),self.hub.settings.send_timeout_seconds)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope,receive,send)
        finally:
            self.hub.release(self.token)
            await self.body_iterator.aclose()

router=APIRouter()
def internal_authorized(request, hub):
    headers=request.headers
    peer=request.client.host if request.client else ''
    if not hub.settings.enabled or not hub.settings.producer_token or not loopback(peer):
        return False
    if headers.get('origin') or headers.get('tailscale-user-login') or headers.get('x-forwarded-proto'):
        return False
    return hmac.compare_digest(headers.get('authorization',''), 'Bearer '+hub.settings.producer_token)

@router.get('/api/v1/camera/status')
async def camera_status(request: Request, watch: bool = False):
    hub=request.app.state.live_camera
    if watch and hub.settings.enabled:
        hub.request_preview() # short authenticated viewing intent bootstraps demand-driven encoding
    return hub.status()

@router.get('/api/v1/camera/mjpeg')
async def camera_mjpeg(request: Request, frames: int | None = None):
    if frames is not None and not 1 <= frames <= 60:
        raise HTTPException(400,'frames must be1..60')
    hub=request.app.state.live_camera
    return MjpegResponse(hub,hub.acquire(),frames)

@router.get('/internal/camera/demand')
async def producer_demand(request: Request):
    hub=request.app.state.live_camera
    if not internal_authorized(request,hub):
        raise HTTPException(403,'private producer only')
    return {'viewers':hub.demand(),'lease_ms':1000,'actuator_execution':False}

@router.post('/internal/camera/frame')
async def producer_frame(request: Request):
    hub=request.app.state.live_camera
    if not internal_authorized(request,hub):
        raise HTTPException(403,'private producer only')
    try:
        encoded=request.headers.get('x-frame-meta','')
        if len(encoded)>8192:
            raise ValueError('metadata header bound')
        meta=decode_cached_object(base64.b64decode(encoded,validate=True).decode('utf-8'),4096)
        data=bytearray()
        async for chunk in request.stream():
            if len(data)+len(chunk)>hub.settings.max_jpeg_bytes:
                raise ValueError('frame exceeds budget')
            data.extend(chunk)
        await hub.publish(bytes(data),meta)
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError) as error:
        hub.rejected+=1
        raise HTTPException(400,str(error)) from error
    return {'accepted':True,'frame_id':meta['frame_id'],'actuator_execution':False}
