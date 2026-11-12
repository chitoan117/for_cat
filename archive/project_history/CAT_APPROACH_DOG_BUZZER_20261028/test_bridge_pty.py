"""Actual C++ bridge + PTY + canonical-schema temporary SQLite, no real USB/camera."""
import json
import os
from pathlib import Path
import pty
import select
import sqlite3
import struct
import subprocess
import sys
import time
import tty

ROOT=Path(__file__).resolve().parent
def crc(data):
 value=0xffff
 for byte in data:
  value ^= byte << 8
  for _ in range(8):value=((value << 1)^0x1021)&0xffff if value&0x8000 else (value << 1)&0xffff
 return value
def encode(rid,cmd,payload):
 body=struct.pack('<BIBH',1,rid,cmd,len(payload))+payload
 return b'\xa5\x5a'+body+struct.pack('<H',crc(body))

def run_case(species,reviewed):
 folder=ROOT/('pty_'+species+('_reviewed' if reviewed else '_unreviewed'))
 folder.mkdir(exist_ok=False)
 master,slave=pty.openpty();tty.setraw(slave);os.set_blocking(master,False)
 dbpath=folder/'events.db';db=sqlite3.connect(str(dbpath),isolation_level=None)
 db.execute('CREATE TABLE ai_latest(id INTEGER PRIMARY KEY,body TEXT)')
 db.execute('CREATE TABLE feed_dry_run_requests(request_id TEXT PRIMARY KEY,body TEXT,decision TEXT)')
 for source in ('MANUAL','SCHEDULED'):
  body={'request_id':source,'source':source,'sub_source':'APP' if source=='MANUAL' else '', 'target_grams':35}
  db.execute('INSERT INTO feed_dry_run_requests VALUES(?,?,NULL)',(source,json.dumps(body)))
 log=(folder/'process.log').open('wb')
 process=subprocess.Popen([str(ROOT/'esp32_bridge'),'--device',os.ttyname(slave),'--db',str(dbpath),'--log',str(folder/'bridge.jsonl'),'--seconds','6','--dog-warning','1','--roi-mode','ROI_ENABLED'],stdout=log,stderr=subprocess.STDOUT)
 fixture=json.loads((ROOT/('production.synthetic.json' if (ROOT/'production.synthetic.json').exists() else 'fixture.json')).read_text())
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 start=time.monotonic();link=0;commands=[];pending=bytearray();step=0;event_at=None;completed=0
 try:
  while time.monotonic()-start<5:
   now=time.monotonic();elapsed=now-start;uptime=1000+int(elapsed*1000);step+=1
   ai={'classification':species,'confidence':.9,'health':'ONLINE','host_boot_id':boot,'actuator_execution':False,
       'updated_monotonic_ms':int(now*1000),'roi_observation_ms':int(now*1000),'roi_sequence':step,
       'roi_calibrated':reviewed,'roi_revision':'SYNTHETIC_PTY_TEST_ONLY',
       'roi_mode':'ROI_ENABLED','roi_config_valid':True,'bbox_available':True,'roi_decision_eligible':reviewed}
   db.execute('INSERT OR REPLACE INTO ai_latest VALUES(1,?)',(json.dumps(ai),))
   fixture['monotonic_ms']=uptime
   for channel in fixture.get('ultrasonic',{}).values():
    if channel.get('last_update') is not None:channel['last_update']=(uptime-channel['sample_age_ms'])&0xffffffff
    if channel.get('last_valid_update') is not None:channel['last_valid_update']=channel['last_update']
   os.write(master,(json.dumps(fixture,separators=(',',':'))+'\n').encode())
   confirmed=elapsed>=2.5
   if confirmed and event_at is None:event_at=uptime
   sample={'boot_nonce':123,'link_token':link,'monotonic_ms':uptime,'sample_ms':uptime,'valid':True,
           'distance_cm':19 if confirmed else 35,'state':'APPROACH_CONFIRMED' if confirmed else 'ARMED',
           'event_id':1 if confirmed else 0,'event_ms':event_at or 0,'warning_completed':completed,'buzzer_phase':0,
           'servo_locked':True,'pump_locked':True}
   os.write(master,('APPROACH '+json.dumps(sample)+'\n').encode())
   wait=time.monotonic()+.2
   while time.monotonic()<wait:
    if select.select([master],[],[],.02)[0]:
     try:pending.extend(os.read(master,4096))
     except BlockingIOError:pass
    while len(pending)>=10:
     assert pending[:2]==b'\xa5\x5a',repr(pending)
     n=struct.unpack_from('<H',pending,8)[0];size=n+12
     if len(pending)<size:break
     frame=bytes(pending[:size]);del pending[:size]
     assert crc(frame[2:-2])==struct.unpack_from('<H',frame,size-2)[0]
     rid=struct.unpack_from('<I',frame,3)[0];cmd=frame[7];payload=frame[10:-2]
     assert cmd in (0x30,0x31),'unexpected command / potential feed TX'
     commands.append(cmd)
     if cmd==0x30:link=struct.unpack_from('<I',payload,5)[0]
     else:
      assert struct.unpack_from('<I',payload,5)[0]==link
      completed=1
     os.write(master,encode(rid,6,bytes([cmd,0]))+b'\r\n')
  cached=json.loads(db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone()[0])
  assert cached['feed_tx_enabled'] is False and cached['pump_tx_enabled'] is False and cached['serial_tx_scope']=='DOG_WARNING_ONLY_NO_FEED_COMMANDS'
  process.wait(timeout=5)
  assert process.returncode==0,(folder/'process.log').read_text()
  auto=[json.loads(row[0]) for row in db.execute("SELECT body FROM esp32_events WHERE kind='feed_request_dry_run'")]
  generated=[r for r in auto if r.get('source')=='AUTO_CAT']
  assert commands.count(0x31)==(1 if species=='DOG' and reviewed else 0),commands
  assert len(generated)==(1 if species=='CAT' and reviewed else 0),generated
  if generated:assert generated[0]['status']=='DRY_RUN_BLOCKED' and generated[0]['qualification_reason']=='WEIGHT_NOT_CALIBRATED' and generated[0]['actuator_execution'] is False
  for request_id,decision in db.execute('SELECT request_id,decision FROM feed_dry_run_requests'):
   result=json.loads(decision);assert result['status']=='DRY_RUN_BLOCKED' and result['actuator_execution'] is False,request_id
  return {'species':species,'roi_reviewed':reviewed,'commands':commands,'auto_candidates':len(generated),'manual_scheduled':'UNCHANGED_DRY_RUN_BLOCKED','result':'PASS'}
 finally:
  if process.poll() is None:process.terminate();process.wait(timeout=3)
  db.close();log.close();os.close(master);os.close(slave)

if __name__=='__main__':
 print(json.dumps([run_case('DOG',True),run_case('CAT',True),run_case('DOG',False)],indent=2))
