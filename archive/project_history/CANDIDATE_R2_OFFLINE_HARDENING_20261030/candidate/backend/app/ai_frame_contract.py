"""Versioned AI stdout adapter; sole ai_latest writer, never a feed interface.

Old detector stdout is accepted after its unchanged ENGINE_CONTRACT marker.
New producer records retain capture freshness/attribution and bounded metadata.
No schema migration: one atomic UPSERT of existing ai_latest(id=1,body).
"""
from collections import deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
import time

PREFIX='FORCAT_FRAME_V1 '
SOURCE='EXISTING_CPP_TENSORRT_OPTIONAL_FOOD_ROI'
MAX_LINE=16384
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate key')
        result[k]=v
    return result
def number(value):return type(value) in (int,float) and math.isfinite(value)
def integer(value):return type(value) is int and 0<=value<2**63
def validate(data,now_ms,boot):
    if not isinstance(data,dict) or data.get('ai_schema_version')!=1 or type(data.get('ai_schema_version')) is not int:raise ValueError('AI schema')
    if data.get('source')!=SOURCE or data.get('data_source')!='REAL' or data.get('simulated') is not False or data.get('actuator_execution') is not False:raise ValueError('AI attribution')
    if not boot or data.get('host_boot_id')!=boot:raise ValueError('wrong host boot')
    epoch=data.get('producer_epoch')
    if not isinstance(epoch,str) or not 1<=len(epoch)<=128:raise ValueError('producer epoch')
    if data.get('health') not in ('ONLINE','DISCONNECTED'):raise ValueError('AI health')
    if data.get('health')=='DISCONNECTED':
        data={**data,'classification':'UNKNOWN','confidence':None,'updated_monotonic_ms':now_ms,
              'roi_decision_eligible':False,'roi_sequence':0,'source_frame_id':0,'detections':[]}
        return data
    for key in ('source_frame_id','roi_sequence','roi_observation_ms','updated_monotonic_ms'):
        if not integer(data.get(key)):raise ValueError('AI identity/timestamp')
    if data['source_frame_id']==0 or data['roi_sequence']==0 or data['updated_monotonic_ms']!=data['roi_observation_ms'] or not 0<=now_ms-data['roi_observation_ms']<=1500:raise ValueError('stale/mismatched AI frame')
    species=data.get('classification');confidence=data.get('confidence')
    if species not in ('CAT','DOG','NONE','UNKNOWN'):raise ValueError('AI species')
    if species in ('CAT','DOG') and (not number(confidence) or not 0<=confidence<=1):raise ValueError('confidence')
    if species in ('NONE','UNKNOWN') and confidence is not None:raise ValueError('no-object confidence')
    if data.get('roi_mode') not in ('FULL_FRAME','ROI_ENABLED') or type(data.get('roi_decision_eligible')) is not bool:raise ValueError('ROI contract')
    if species!='UNKNOWN' and not data['roi_decision_eligible']:raise ValueError('unqualified AI')
    if data['roi_mode']=='ROI_ENABLED' and species!='UNKNOWN' and data.get('roi_calibrated') is not True:raise ValueError('unreviewed ROI')
    if any(not integer(data.get(k)) or not 2<=data[k]<=4096 for k in ('frame_width','frame_height')):raise ValueError('AI dimensions')
    boxes=data.get('detections')
    if not isinstance(boxes,list) or len(boxes)>8:raise ValueError('AI boxes')
    for box in boxes:
        if not isinstance(box,dict) or box.get('species') not in ('CAT','DOG'):raise ValueError('bbox species')
        b=box.get('bbox')
        if not isinstance(b,dict) or any(not number(b.get(k)) for k in ('x1','y1','x2','y2')):raise ValueError('bbox')
        if not 0<=b['x1']<b['x2']<=1 or not 0<=b['y1']<b['y2']<=1:raise ValueError('bbox coordinates')
    return data

class WriterLock:
    def __init__(self,path):self.path=Path(str(path)+'-ai.lock');self.file=None
    def __enter__(self):
        self.file=self.path.open('a+b')
        try:
            import os
            if os.name=='nt':
                import msvcrt
                self.file.seek(0);self.file.write(b'\0');self.file.flush();self.file.seek(0)
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException:self.file.close();self.file=None;raise
        return self
    def __exit__(self,*_):
        if self.file:self.file.close();self.file=None

class StateTap:
    def __init__(self,path,boot,clock=time.monotonic):
        self.path=Path(path);self.boot=boot;self.clock=clock
        self.legacy=False;self.modern=False;self.epoch=None;self.sequence=0;self.frame=0
        self.retired=deque(maxlen=16);self.rejected=0;self.storage_errors=0
    def write(self,data):
        body=json.dumps(data,separators=(',',':'),allow_nan=False)
        if len(body.encode('utf-8'))>4096:raise ValueError('canonical cache bound')
        # Fresh short connection/transaction; no history/image insertion.
        try:
            with sqlite3.connect(self.path,timeout=.02) as db:
                db.execute('CREATE TABLE IF NOT EXISTS ai_latest(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
                db.execute('INSERT INTO ai_latest VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(body,))
            return True
        except sqlite3.Error:
            self.storage_errors+=1;return False
    def disconnected(self):
        return self.write({'health':'DISCONNECTED','classification':'UNKNOWN','confidence':None,
            'source':SOURCE if self.modern else 'EXISTING_CPP_TENSORRT_STDOUT','host_boot_id':self.boot,
            'updated_monotonic_ms':int(self.clock()*1000),'actuator_execution':False,'data_source':'REAL',
            'simulated':False,'producer_epoch':self.epoch,'ai_schema_version':1})
    def accept(self,line):
        if len(line.encode('utf-8'))>MAX_LINE:self.rejected+=1;return False
        try:
            if line.startswith(PREFIX):
                data=validate(json.loads(line[len(PREFIX):],object_pairs_hook=unique),int(self.clock()*1000),self.boot)
                epoch=data['producer_epoch']
                if epoch in self.retired:raise ValueError('retired producer')
                if epoch==self.epoch and data['health']=='ONLINE' and (data['roi_sequence']<=self.sequence or data['source_frame_id']<=self.frame):raise ValueError('duplicate/reordered frame')
                # Commit first; storage failure cannot advance replay watermark.
                if not self.write(data):return False
                if epoch!=self.epoch:
                    if self.epoch:self.retired.append(self.epoch)
                    self.epoch=epoch;self.sequence=self.frame=0
                if data['health']=='ONLINE':self.sequence=data['roi_sequence'];self.frame=data['source_frame_id']
                self.modern=True;return True
            if self.modern:raise ValueError('legacy metadata cannot overwrite frame schema')
            if line.startswith('ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16;'):self.legacy=True;return False
            if not self.legacy or ' MODE=' not in line or ' PROCESSED=' not in line:return False
            species='NONE';confidence=None
            if line.startswith('DETECTIONS '):
                items=re.findall(r'(CAT|DOG)=([0-9]+(?:\.[0-9]+)?)',line)
                if not items:raise ValueError('legacy detections')
                scores=[(s,float(c)) for s,c in items]
                if any(not 0<=c<=1 for _,c in scores):raise ValueError('legacy confidence')
                species,confidence=max(scores,key=lambda p:(p[0]=='DOG',p[1]))
            elif not line.startswith('NONE MODE='):return False
            return self.write({'health':'ONLINE','classification':species,'confidence':confidence,
                'source':'EXISTING_CPP_TENSORRT_STDOUT','data_source':'REAL','simulated':False,
                'host_boot_id':self.boot,'updated_monotonic_ms':int(self.clock()*1000),
                'last_observation_at':datetime.now(timezone.utc).isoformat(),'actuator_execution':False,
                'frame_metadata_available':False})
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):self.rejected+=1;return False
