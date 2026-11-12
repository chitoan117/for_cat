"""Measured meal observations; this API never starts a feeder or pump."""
from contextlib import closing
from pathlib import Path
from typing import Literal
import json,math,os,sqlite3,tempfile,time
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import BaseModel,ConfigDict

router=APIRouter(prefix='/api/meal-observation')
CMD_FILE=Path('/tmp/for_cat_cmd.txt')

class Action(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['SELECT_A','SELECT_B','FINISH']

def finite(x):return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)

def snapshot(db_path):
    with closing(sqlite3.connect(str(db_path),timeout=.5)) as db:
        row=db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()
        rows=db.execute("SELECT seq,occurred_at,body FROM esp32_events WHERE kind='meal_preference' ORDER BY seq DESC LIMIT 100").fetchall()
    state=json.loads(row[0]) if row else {}
    fresh=state.get('host_boot_id')==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    stamp=state.get('updated_monotonic_ms')
    fresh=fresh and finite(stamp) and 0<=time.monotonic()*1000-stamp<2500
    fc=(state.get('telemetry') or {}).get('fc_live') or {}
    live=fc if fresh and fc.get('meal_schema_version')==2 else None
    records=[];seen=set()
    for seq,at,body in rows:
        try:m=json.loads(body)
        except (ValueError,TypeError):continue
        ident=m.get('meal_id');a=m.get('starting_g');b=m.get('remaining_g');c=m.get('consumed_g')
        if not (m.get('schema_version')==2 and m.get('final') is True and isinstance(ident,str) and ident and ident not in seen):continue
        if m.get('food') not in ('FOOD_A','FOOD_B') or not all(finite(x) for x in (a,b,c)) or not 0<=b<=a or a<=0 or abs(c-(a-b))>.1:continue
        seen.add(ident)
        records.append({**m,'id':ident,'seq':seq,'timestamp':at})
        if len(records)>=20:break
    return {'live':live,'records':records,'window_seconds':120,'measurement_source':'LOADCELL_MASS_DIFFERENCE'}

def queue_command(command):
    fd,name=tempfile.mkstemp(prefix='forcat_meal_',suffix='.txt',dir=str(CMD_FILE.parent))
    try:
        with os.fdopen(fd,'w') as f:f.write(command+'\n')
        try:os.link(name,str(CMD_FILE))
        except FileExistsError:raise HTTPException(409,'Đang xử lý lệnh khác, thử lại sau.')
    finally:Path(name).unlink(missing_ok=True)

@router.get('')
def get_observation(request:Request):
    return snapshot(request.app.state.store_path)

@router.post('',status_code=202)
def observation_action(body:Action,request:Request,response:Response):
    current=snapshot(request.app.state.store_path);live=current['live']
    if not live:raise HTTPException(503,'Chưa có dữ liệu cân mới từ ESP32.')
    if body.action=='FINISH':
        if live.get('meal_phase')!='OBSERVING' or live.get('meal_stable') is not True or (live.get('meal_elapsed_seconds') or 0)<10:
            raise HTTPException(409,'Cần bữa ăn thật và số cân ổn định trước khi kết thúc.')
        command='eval'
    else:
        if live.get('bench_state') not in ('READY','CAT FAULT*','MASS OK GATE?'):
            raise HTTPException(409,'Đợi cửa cấp thức ăn dừng trước khi đổi món.')
        command='a' if body.action=='SELECT_A' else 'b'
    queue_command(command)
    return {'queued':True,'action':body.action,'applied':False}
