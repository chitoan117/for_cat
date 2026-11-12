from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.water_control import view,enqueue
router=APIRouter(prefix='/api/water-control')
class Action(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    action:Literal['ENABLE','DISABLE']
    confirmed:bool=False
@router.get('')
def status(request:Request):return view(request.app.state.store_path)
@router.post('',status_code=202)
def change(body:Action,request:Request):
    path=request.app.state.store_path
    if body.action=='ENABLE':
        if not body.confirmed:raise HTTPException(422,'Cần xác nhận trước khi bật chức năng nước.')
        current=view(path)
        if not current['supported']:raise HTTPException(503,'Chưa có kết nối mới với ESP32.')
        if not current['can_enable']:raise HTTPException(409,'Cần D1 có số đo và thiết bị không bận trước khi bật.')
    try:enqueue(path,body.request_id,body.action)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return {'queued':True,'applied':False,'request_id':body.request_id,'action':body.action}
