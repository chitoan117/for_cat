"""Same backend/database, read-only ESP32 bridge API; no serial port here."""
from fastapi import APIRouter, HTTPException, Request
from app.device_state import owner_verification

router = APIRouter(prefix='/api/v1/esp32')


@router.get('/status')
def esp32_status(request: Request):
    reader = getattr(request.app.state, 'esp32_reader', None)
    if reader is None:
        raise HTTPException(status_code=503, detail='ESP32 bridge integration not configured')
    state = reader.status()
    state['owner_verification'] = owner_verification()
    state['feed_target_grams'] = 35
    state['feeding_execution'] = 'UNATTENDED_SAFE_MODE_BLOCKED'
    return state


@router.get('/events')
def esp32_events(request: Request, limit: int = 50):
    reader = getattr(request.app.state, 'esp32_reader', None)
    if reader is None:
        raise HTTPException(status_code=503, detail='ESP32 bridge integration not configured')
    return reader.events(limit)
