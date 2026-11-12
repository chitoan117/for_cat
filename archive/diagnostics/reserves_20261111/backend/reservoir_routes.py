import asyncio,time
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict
from app.reservoir_levels import SENSORS,save_full
router=APIRouter(prefix='/api/reservoir-calibration')
class FullRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    role:Literal['food','water']
    confirmed:bool=False
@router.post('')
async def capture(body:FullRequest,request:Request):
    if not body.confirmed:raise HTTPException(422,'Cần xác nhận hộp/bình đã đầy.')
    values=[];seen=set();end=time.monotonic()+12
    while len(values)<5 and time.monotonic()<end:
        state=request.app.state.system_state.snapshot()
        sensor=(state.get('ultrasonic') or {}).get(SENSORS[body.role][0]) or {}
        if state.get('data_source')!='REAL' or not state.get('esp32',{}).get('connected') or sensor.get('valid') is not True:
            raise HTTPException(409,'Chưa có số đo mới từ cảm biến dự trữ.')
        stamp=sensor.get('last_update')
        if stamp is not None and stamp not in seen:
            seen.add(stamp);values.append(sensor['distance_cm'])
        if len(values)<5:await asyncio.sleep(.2)
    try:full=save_full(Path(request.app.state.store_path).parent/'reservoir_calibration.json',body.role,values)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return {'saved':True,'role':body.role,'full_cm':full}
