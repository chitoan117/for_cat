"""Windows offline E2E runner: native production cores -> SIMULATION SQLite.

No SSH/network/serial/camera imports. The database path is deliberately NOT a CLI
parameter: every execution exclusively creates a new sandbox simulation.sqlite3.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import struct
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
PAYLOAD=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/payload'
HOST=PAYLOAD/'jetson/device'
FW=ROOT/'FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32'
ZIG=ROOT/'.tools-zig/zig-x86_64-windows-0.16.0/zig.exe'
EPOCH=datetime(2026,10,28,tzinfo=timezone.utc)
sys.path.insert(0,str(PAYLOAD/'jetson'))
from app.dry_run_requests import DryRunRequests

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fake_iso(ms):return (EPOCH+timedelta(milliseconds=ms)).isoformat()
def create_database(path,run_dir):
    if path.name!='simulation.sqlite3' or path.parent.resolve()!=run_dir.resolve() or OUT.resolve() not in path.resolve().parents:
        raise ValueError('test database must belong to the exclusive milestone run directory')
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    db=sqlite3.connect(path)
    db.executescript('''
      CREATE TABLE simulation_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE simulation_events(seq INTEGER PRIMARY KEY,scenario TEXT NOT NULL,clock_domain TEXT NOT NULL,
        fake_ms INTEGER NOT NULL,occurred_at TEXT NOT NULL,kind TEXT NOT NULL,
        simulation INTEGER NOT NULL CHECK(simulation=1),physical_execution INTEGER NOT NULL CHECK(physical_execution=0),body TEXT NOT NULL);
      CREATE TABLE simulation_feeds(request_id TEXT PRIMARY KEY,status TEXT NOT NULL,actual_dispensed_grams REAL,
        occurred_at TEXT NOT NULL,simulation INTEGER NOT NULL CHECK(simulation=1),body TEXT NOT NULL);
      CREATE TABLE simulation_meals(request_id TEXT PRIMARY KEY,food_name TEXT NOT NULL,starting_mass REAL,
        remaining_mass REAL,consumed_mass REAL,classification TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT NOT NULL,
        simulation INTEGER NOT NULL CHECK(simulation=1),body TEXT NOT NULL);
    ''')
    db.execute('INSERT INTO simulation_meta VALUES(?,?)',('mode','SIMULATION_ONLY_NOT_PRODUCTION'))
    DryRunRequests.ensure_schema(db);db.commit()
    return db

class ReplayDateTime(datetime):
    fake_ms=0
    @classmethod
    def now(cls,tz=None):
        value=EPOCH+timedelta(milliseconds=cls.fake_ms)
        return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

def validate(db,records):
    def where(kind):return [e for e in records if e['kind']==kind]
    def scenario(number):return next(e for e in where('SCENARIO_RESULT') if e['scenario_number']==number)
    assert len(where('SCENARIO_RESULT'))==4
    assert all(scenario(i)['status']=='PASS' for i in range(1,5))
    one=scenario(1);assert one['actual_dispensed_grams']==35 and one['request_count']==1 and one['servo_final_degrees']==90
    dog=scenario(2);assert dog['dog_warnings']==1 and dog['buzzer_pulse_count']==2 and dog['servo_new_opens']==0
    for n,food,remaining,consumed,label in ((3,'FOOD_A',5,30,'LIKE'),(4,'FOOD_B',30,5,'DISLIKE')):
        result=scenario(n)
        assert result['food_name']==food and result['starting_mass']==35 and result['remaining_mass']==remaining and result['consumed_mass']==consumed and result['classification']==label and result['observation_ms']==60000
    primary=[e for e in records if e['clock_domain']=='PRIMARY']
    requests=[e for e in primary if e['kind']=='AUTO_CAT_REQUEST'];assert len(requests)==2
    assert requests[1]['fake_ms']-requests[0]['fake_ms']>=7200000
    feeds=[e for e in primary if e['kind']=='FEED_COMPLETED'];assert len(feeds)==2 and sum(e['actual_dispensed_grams'] for e in feeds)==70
    assert feeds[-1]['daily_portions']==2 and feeds[-1]['daily_grams']==70
    opens=[e for e in primary if e['kind']=='SIMULATED_SERVO' and e['state']=='OPEN'];assert len(opens)==2
    assert all(e['angle_degrees']==45 for e in opens)
    assert all(e['angle_degrees']==90 for e in primary if e['kind']=='SIMULATED_SERVO' and e['state']=='CLOSED')
    assert not any(e['kind']=='SIMULATED_SERVO' for e in primary if e['scenario'] in ('SCENARIO_2_DOG_WARNING','SCENARIO_3_FOOD_A'))
    edges=[e for e in primary if e['scenario']=='SCENARIO_2_DOG_WARNING' and e['kind']=='SIMULATED_BUZZER_EDGE']
    assert [e['level'] for e in edges]==['LOW','HIGH','LOW','HIGH']
    assert [e['fake_ms']-edges[0]['fake_ms'] for e in edges]==[0,200,400,600]
    meals=[e for e in primary if e['kind']=='MEAL_PREFERENCE'];assert len(meals)==2
    for m in meals:assert m['observation_finished_ms']-m['observation_started_ms']==60000
    assert db.execute('SELECT COUNT(*) FROM simulation_events').fetchone()[0]==len(records)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    by_request={e['request_id']:e for e in records if e['kind']=='AUTO_CAT_REQUEST'}
    for request_id,body,decision in db.execute('SELECT request_id,body,decision FROM feed_dry_run_requests'):
        request=json.loads(body)
        assert request['actuator_execution'] is False and request['actual_dispensed_grams'] is None
        assert request['timestamp']==fake_iso(by_request[request_id]['fake_ms'])
        if decision:assert json.loads(decision)['production_policy_actuator_execution'] is False
    error_ids={e['request_id'] for e in where('FEED_ERROR')}
    assert not error_ids.intersection({e['request_id'] for e in where('FEED_COMPLETED')})
    assert all(e['servo_closed'] is True for e in where('FEED_ERROR'))
    assert all(e['clock_domain']==by_request[e['request_id']]['clock_domain'] for e in where('FEED_COMPLETED'))
    assert all(e['simulation'] is True and e['production_actuator_execution'] is False and e['physical_hx711_pass'] is False for e in records)
    last={}
    for event in records:
        assert event['fake_ms']>=last.get(event['clock_domain'],0)
        last[event['clock_domain']]=event['fake_ms']
    # Independent Python decoder checks actual bytes emitted by the C++ codec,
    # not just encode->parse using the same implementation.
    wire_frames=where('UART_SIMULATED_TX');corrupt_count=0
    for event in wire_frames:
        frame=bytes.fromhex(event['frame_hex'])
        assert frame[:3]==b'\xa5\x5a\x01'
        request_id=struct.unpack_from('<I',frame,3)[0];length=struct.unpack_from('<H',frame,8)[0]
        assert request_id==event['request_id_wire'] and frame[7]==event['command'] and len(frame)==12+length
        assert frame[7] in (0x30,0x31) and length==(9 if frame[7]==0x30 else 21)
        assert frame[10]==1
        crc=0xffff
        for byte in frame[2:-2]:
            crc^=byte<<8
            for _ in range(8):crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
        matches=crc==struct.unpack_from('<H',frame,len(frame)-2)[0]
        assert matches is not event['crc_corrupt_injected']
        corrupt_count+=int(not matches)
    for frame in where('SIMULATED_CAMERA_DETECTION'):
        assert len(frame['detections'])==frame['detections_count']
        if frame['roi_mode']=='FULL_FRAME':assert frame['tray_membership_proven'] is False
    summary=where('E2E_SUITE_COMPLETED')[-1]
    assert summary['scenario_count']==4 and summary['safety_cases']>=30
    return {'four_scenarios':'PASS','native_safety_cases':summary['safety_cases'],'native_assertions':summary['assertions'],
            'all_events_persisted':True,'event_count':len(records),'primary_requests':len(requests),
            'primary_simulated_successful_feeds':len(feeds),'primary_simulated_actual_grams':70,
            'food_A':'LIKE_30g','food_B':'DISLIKE_5g','buzzer_waveform_ms':[0,200,400,600],
            'sqlite_integrity':'ok','production_inbox_remains_dry_run':True,
            'uart_frames_independently_checked':len(wire_frames),'corrupted_crc_frames_rejected':corrupt_count,
            'bbox_inputs_logged':True}

def main():
    if len(sys.argv)!=1:raise SystemExit('No device/database/mode override is supported. Run without arguments.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir=OUT/'runs'/stamp;run_dir.mkdir(parents=True,exist_ok=False)
    protected=[FW/'include/m4/hx711.h',FW/'include/m4/hx711_reference.h',FW/'include/m4/approach_dog_warning.h',FW/'include/m4/quad_level_sampler.h',
               FW/'include/safety_logic.h',FW/'include/uart_v1.h',FW/'include/dog_warning_protocol.h',FW/'platformio.ini',
               HOST/'food_roi.h',HOST/'roi_species.h',HOST/'approach_fusion.h',HOST/'feed_policy.h',HOST/'decision_logic.h',
               PAYLOAD/'jetson/app/dry_run_requests.py',PAYLOAD/'jetson/app/scheduled_worker.py']
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    # Prove rejected paths cannot reach either filesystem creation or SQLite.
    with patch('os.open',side_effect=AssertionError('unsafe DB creation reached')), patch('sqlite3.connect',side_effect=AssertionError('unsafe SQLite access reached')):
        for invalid in (OUT/'events.db',ROOT/'simulation.sqlite3'):
            try:create_database(invalid,run_dir)
            except ValueError:pass
            else:raise AssertionError('unsafe database path accepted')
    exe=run_dir/'e2e_demo.exe'
    build=subprocess.run([str(ZIG),'c++','-std=c++14','-O1','-g','-Wall','-Wextra','-Wpedantic','-Werror',
                          '-I'+str(HOST),'-I'+str(FW/'include'),str(OUT/'e2e_demo.cpp'),'-o',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    (run_dir/'compile.log').write_bytes(build.stdout)
    if build.returncode:
        print(build.stdout.decode('utf-8','replace'));raise SystemExit(build.returncode)
    db=create_database(run_dir/'simulation.sqlite3',run_dir)
    records=[];summary={'E2E_OFFLINE_DEMO_READY':False,'run_directory':str(run_dir),'mode':'SIMULATION',
                       'jetson_arm_cuda_tensorrt_build':'NOT_VERIFIED_WINDOWS_ONLY','hardware_access':False}
    stderr=(run_dir/'native.stderr.log').open('wb')
    child=subprocess.Popen([str(exe),'--simulation-only',str(int(EPOCH.timestamp()*1000))],stdout=subprocess.PIPE,stderr=stderr,text=True,encoding='utf-8')
    scenario_logs={}
    try:
        with (run_dir/'events.jsonl').open('x',encoding='utf-8') as raw, (run_dir/'timeline.csv').open('x',encoding='utf-8',newline='') as timeline:
            csv_out=csv.writer(timeline);csv_out.writerow(['seq','clock_domain','fake_ms','timestamp','scenario','kind','simulation','physical_execution'])
            for line in child.stdout:
                event=json.loads(line);assert event['seq']==len(records)+1
                assert event['mode']=='SIMULATION' and event['simulation'] is True and event['production_actuator_execution'] is False
                raw.write(line);records.append(event)
                scenario=event['scenario'];filename=scenario if scenario.startswith('SCENARIO_') else 'safety_checks'
                if filename not in scenario_logs:scenario_logs[filename]=(run_dir/(filename+'.jsonl')).open('x',encoding='utf-8')
                scenario_logs[filename].write(line)
                at=fake_iso(event['fake_ms']);csv_out.writerow([event['seq'],event['clock_domain'],event['fake_ms'],at,scenario,event['kind'],1,0])
                body=json.dumps(event,allow_nan=False)
                db.execute('INSERT INTO simulation_events VALUES(?,?,?,?,?,?,?,?,?)',(event['seq'],scenario,event['clock_domain'],event['fake_ms'],at,event['kind'],1,0,body))
                if event['kind']=='AUTO_CAT_REQUEST':
                    ReplayDateTime.fake_ms=event['fake_ms']
                    with patch('app.dry_run_requests.datetime',ReplayDateTime):
                        DryRunRequests.enqueue_in_transaction(db,event['request_id'],'AUTO_CAT','',35)
                elif event['kind']=='ARBITER_DECISION':
                    # Idempotent production dry-run decision is never overwritten by a retry.
                    db.execute('UPDATE feed_dry_run_requests SET decision=? WHERE request_id=? AND decision IS NULL',(body,event['request_id']))
                elif event['kind'] in ('FEED_COMPLETED','FEED_ERROR'):
                    db.execute('INSERT INTO simulation_feeds VALUES(?,?,?,?,?,?)',(event['request_id'],event.get('status','SIMULATION_ERROR'),event.get('actual_dispensed_grams'),at,1,body))
                elif event['kind']=='MEAL_PREFERENCE':
                    db.execute('INSERT INTO simulation_meals VALUES(?,?,?,?,?,?,?,?,?,?)',(event['request_id'],event['food_name'],event['starting_mass'],event['remaining_mass'],event['consumed_mass'],event['classification'],fake_iso(event['observation_started_ms']),fake_iso(event['observation_finished_ms']),1,body))
                if len(records)%256==0:db.commit()
        child.wait(timeout=30);db.commit()
        if child.returncode:raise RuntimeError((run_dir/'native.stderr.log').read_text(encoding='utf-8'))
        summary.update(validate(db,records))
        after={str(p.relative_to(ROOT)):sha(p) for p in protected};assert before==after
        summary['production_sources_unchanged_sha256']=after
        summary['native_binary_sha256']=sha(exe)
        summary['E2E_OFFLINE_DEMO_READY']=True
    except Exception as error:
        summary['error']=str(error)
        if child.poll() is None:child.terminate();child.wait(timeout=5)
        db.commit()
    finally:
        for stream in scenario_logs.values():stream.close()
        stderr.close();db.close()
    summary['artifacts_sha256']={p.name:sha(p) for p in run_dir.iterdir() if p.is_file()}
    (run_dir/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (OUT/'latest_run.json').write_text(json.dumps({'run_directory':str(run_dir),'result':summary},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('production_sources_unchanged_sha256','artifacts_sha256')},indent=2))
    if summary['E2E_OFFLINE_DEMO_READY']:
        from make_report import write_report
        write_report(run_dir)
    raise SystemExit(0 if summary['E2E_OFFLINE_DEMO_READY'] else 1)

if __name__=='__main__':main()
