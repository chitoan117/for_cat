"""REST + bounded realtime view over the same SystemState/provider."""
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal
from app.dry_run_requests import DryRunRequests

router = APIRouter()
WEB = Path(__file__).resolve().parents[1] / 'web'


class ManualPreview(BaseModel):
    request_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    sub_source: Literal['KIOSK', 'APP']
    target_grams: Literal[35] = 35


@router.post('/api/feed/preview', status_code=202)
def manual_preview(body: ManualPreview, request: Request):
    if request.app.state.esp32_reader is None:
        raise HTTPException(503, 'C++ arbiter integration not configured')
    try:
        return DryRunRequests(Path(request.app.state.store_path).resolve()).enqueue(body.request_id, 'MANUAL', body.sub_source, body.target_grams)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except OverflowError as error:
        raise HTTPException(503, str(error)) from error


@router.get('/api/feed/preview/{request_id}')
def preview_result(request_id: str, request: Request):
    if request.app.state.esp32_reader is None:
        raise HTTPException(503, 'C++ arbiter integration not configured')
    if len(request_id) > 64:
        raise HTTPException(400, 'invalid request ID')
    result = DryRunRequests(Path(request.app.state.store_path).resolve()).get(request_id)
    if result is None:
        raise HTTPException(404, 'dry-run request not found')
    return result


@router.get('/api/status')
def system_status(request: Request):
    return request.app.state.system_state.snapshot()


@router.get('/kiosk', include_in_schema=False)
@router.get('/app', include_in_schema=False)
def live_page():
    return FileResponse(WEB / 'index.html', headers={'Cache-Control': 'no-store'})


@router.get('/assets/system-state.js', include_in_schema=False)
def live_script():
    return FileResponse(WEB / 'system-state.js', media_type='application/javascript', headers={'Cache-Control': 'no-cache'})


@router.websocket('/api/ws/state')
async def state_socket(websocket: WebSocket):
    origin = websocket.headers.get('origin')
    if origin and urlparse(origin).netloc.lower() != websocket.headers.get('host', '').lower():
        await websocket.close(code=1008)
        return
    service = websocket.app.state.system_state
    queue = service.subscribe()
    if queue is None:
        await websocket.close(code=1013)
        return
    await websocket.accept()
    try:
        await asyncio.wait_for(websocket.send_json(await asyncio.to_thread(service.snapshot)), timeout=2)
        while True:
            state = await queue.get()
            await asyncio.wait_for(websocket.send_json(state), timeout=2)
    except (WebSocketDisconnect, RuntimeError, asyncio.TimeoutError):
        pass
    finally:
        service.unsubscribe(queue)
