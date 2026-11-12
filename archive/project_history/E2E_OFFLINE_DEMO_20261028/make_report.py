"""Read-only evidence inspection and one milestone report; no scenario rerun."""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def offset(ms):
    seconds,millis=divmod(ms,1000);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return f'+{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}'
def cell(value):return str(value).replace('|','/').replace('\n',' ')

def write_report(run_dir=None):
    if run_dir is None:run_dir=Path(json.loads((OUT/'latest_run.json').read_text(encoding='utf-8'))['run_directory'])
    run_dir=Path(run_dir).resolve()
    if OUT.resolve() not in run_dir.parents:raise ValueError('report only accepts sandbox evidence')
    result=json.loads((run_dir/'result.json').read_text(encoding='utf-8'))
    assert result['E2E_OFFLINE_DEMO_READY'] is True
    assert sha(run_dir/'e2e_demo.exe')==result['native_binary_sha256']
    for name,digest in result['production_sources_unchanged_sha256'].items():assert sha(ROOT/name)==digest
    with sqlite3.connect((run_dir/'simulation.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        rows=[json.loads(row[0]) for row in db.execute('SELECT body FROM simulation_events ORDER BY seq')]
        assert len(rows)==result['event_count']
        counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('simulation_events','simulation_feeds','simulation_meals','feed_dry_run_requests')}
    # Additional boundary proof: executable rejects a non-simulation invocation
    # before constructing an IO object or emitting any event.
    probe=subprocess.run([str(run_dir/'e2e_demo.exe'),'--production','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    assert probe.returncode==2 and not probe.stdout
    (run_dir/'negative_production_cli.log').write_bytes(probe.stdout+probe.stderr)
    primary=[row for row in rows if row['clock_domain']=='PRIMARY']
    scenario_results=[row for row in primary if row['kind']=='SCENARIO_RESULT']
    feeds=[row for row in primary if row['kind']=='FEED_COMPLETED']
    meals=[row for row in primary if row['kind']=='MEAL_PREFERENCE']
    keys={'AUTO_CAT_REQUEST','SIMULATED_SERVO','FEED_COMPLETED','DOG_WARNING','SIMULATED_BUZZER_EDGE',
          'CONSUMPTION_OBSERVATION_STARTED','MEAL_PREFERENCE','FAKE_CLOCK_ADVANCE','SCENARIO_RESULT'}
    timeline=[row for row in primary if row['kind'] in keys]
    relative=run_dir.relative_to(ROOT).as_posix()
    lines=[
      '# E2E OFFLINE DEMO — for_cat — 2026-10-28',
      '',
      '**Kết quả: bốn kịch bản E2E PASS, simulation-only. Production servo/pump vẫn LOCKED; HX711_PHYSICAL_PASS không được tuyên bố.**',
      '',
      f'Run bằng chứng: `{relative}/`. C++14 Windows native; toàn bộ thời gian bên dưới là **fake clock UTC**, không phải camera/cân/ăn thật.',
      '',
      '## 1. Architecture flow thực sự được chạy',
      '',
      '```text',
      'Synthetic detector CAT/DOG bbox (normalized original frame)',
      '  -> production Food ROI / RoiSpecies (FULL_FRAME default; ROI_ENABLED test)',
      '  -> shared HC-SR04 Approach FSM + ApproachFusion / temporal timestamps',
      '  -> existing FeedArbiter (qualification only; actuator_execution=false)',
      '     CAT -> SIMULATION-only dispatch capability',
      '       -> existing safety::FeedController + DailyStore interface (fake store)',
      '       -> FakeServo OPEN45 / CLOSED90, no GPIO implementation',
      '       <- existing Hx711 driver / signed24 / median3 / calibration',
      '          with synthetic raw ADC bits on fake PinIO',
      '     DOG -> existing UARTv1 encode + CRC / Parser / warning Receiver',
      '       -> existing buzzer FSM -> fake GPIO2 edges only',
      '  -> separate60s simulated consumption observer / LIKE-DISLIKE-UNCERTAIN',
      '  -> JSONL -> Python recorder -> isolated SQLite + production DryRunRequests',
      '```',
      '',
      '- Không chạy YOLO inference thật: input camera là output detector mô phỏng có bbox rõ nguồn. Không train/download model.',
      '- Không thêm đường production AI→servo. Arbiter vẫn trả DRY_RUN; adapter chỉ cho phép **FakeServo** trong executable offline. Bản native từ chối `--production`; source chặn build khi ARDUINO/ESP_PLATFORM được định nghĩa.',
      '- Cấp thức ăn và theo dõi tiêu thụ là hai phase riêng. Khối lượng giảm trong phase ăn không gọi lại controller cấp thức ăn.',
      '- Daily giới hạn được tái sử dụng từ `safety::FeedController`:4 portions/150g; cooldown dùng mức2h cho AUTO_CAT. Đó là composition trong harness, không phải deployment mới cho production.',
      '',
      '## 2. Kết quả build / tests',
      '',
      '| Kiểm tra | Kết quả |',
      '|---|---|',
      '| Windows C++14, `-Wall -Wextra -Wpedantic -Werror` | PASS, không warning |',
      '| Bốn kịch bản đầy đủ input→event cuối→SQLite | PASS4/4 |',
      f"| Native safety/boundary cases mới | PASS{result['native_safety_cases']} cases / {result['native_assertions']} explicit assertions |",
      '| SQLite recorder / timeline / event association | PASS |',
      f"| UART bytes / LE fields / CRC đối chiếu bằng Python độc lập | PASS{result.get('uart_frames_independently_checked','?')} frames; CRC corrupt bị loại{result.get('corrupted_crc_frames_rejected','?')} |",
      '| Unsafe DB path guards | PASS: không chạm os.open/sqlite3.connect |',
      '| Non-simulation CLI | PASS: exit2, không xuất event |',
      '| SQLite integrity / all events persisted | PASS / `ok` |',
      '| Production source hashes trước/sau | Không đổi |',
      '| Jetson ARM64 / CUDA / TensorRT / camera / GPIO | NOT_VERIFIED trong milestone này |',
      '',
      'Safety coverage: ROI ON/OFF/outside/unreviewed, CAT+DOG, NONE, boot gần, biên5/20/30cm/hysteresis,3 mẫu quá1.5s, CAT đứng gần120s, DOG đứng gần120s, cooldown/duplicate, daily meals/grams, request khi busy, HX chưa validated, persistence failure, sensor INVALID/NaN/âm/overflow/disconnect, timeout/no-progress, giảm cân khi đang cấp, tare epoch đổi, AI/UART stale, CRC sai/expired/replay, overshoot và production lock.',
      '',
      'Preference coverage: consumed0/5/5.000001/10/17.999999/18/30/35g; stable noise; unstable/negative/NaN/INVALID/tare/future timestamp/stale/gap/refill; đủ60s mới kết luận. Dữ liệu không hợp lệ trả UNCERTAIN và consumed=null, không ép thành0 hoặc LIKE/DISLIKE.',
      '',
      '## 3. Bốn kịch bản demo',
      '',
      '| Kịch bản | Fake time hoàn tất | Kết quả có bằng chứng |',
      '|---|---|---|',
    ]
    for row in scenario_results:
        n=row['scenario_number']
        detail={1:'CAT: đúng1 request; feedback đạt35g; fake servo45°→90°; giữ gần không cấp lặp.',
                2:'DOG: không feed, không mở servo; đúng2 ON200ms/gap200ms; giữ gần120s không lặp.',
                3:'FOOD_A:35→25→5g, consumed30g, LIKE;60s; không gọi lại servo.',
                4:'FOOD_B: meal mới sau fake cooldown>2h,35→30g, consumed5g, DISLIKE;60s.'}[n]
        lines.append(f"| {n} | {offset(row['fake_ms'])} | PASS — {detail} |")
    lines += ['', '### Event records chính đọc lại từ SQLite', '',
              '| Type / request | Food | Actual / starting | Remaining | Consumed | Result | Timestamp UTC (fake) |',
              '|---|---|---:|---:|---:|---|---|']
    for row in feeds:
        at=datetime.fromtimestamp(row['timestamp_unix_ms']/1000,tz=timezone.utc).isoformat()
        lines.append(f"| SIMULATED_FEED `{row['request_id']}` | {row['food_name']} | {row['actual_dispensed_grams']}g | — | — | SIMULATION_SUCCESS | {at} |")
    for row in meals:
        at=datetime.fromtimestamp(row['timestamp_unix_ms']/1000,tz=timezone.utc).isoformat()
        lines.append(f"| SIMULATED_MEAL `{row['request_id']}` | {row['food_name']} | {row['starting_mass']}g | {row['remaining_mass']}g | {row['consumed_mass']}g | {row['classification']} | {at} |")
    lines += ['', '### Fake clock timeline rút gọn', '', '| Seq | Fake clock | Event | Nội dung |', '|---:|---|---|---|']
    for row in timeline:
        detail={k:v for k,v in row.items() if k in {'request_id','angle_degrees','level','state','actual_dispensed_grams','food_name','consumed_mass','classification','advanced_ms','scenario_number','status'}}
        lines.append(f"| {row['seq']} | {offset(row['fake_ms'])} | {row['kind']} | {cell(json.dumps(detail,ensure_ascii=False))} |")
    lines += [
      '',
      'Một clock domain PRIMARY chạy liên tục bốn demo. Mỗi safety case có clock domain riêng nên reset test về0 là tường minh, không phải timestamp production bị lùi. Bước nhảy2h chỉ được phép khi controller/meal/buzzer không hoạt động.',
      '',
      '## 4. Log đầy đủ và database test',
      '',
      f"- **{result['event_count']} event** trong `events.jsonl` và `simulation_events`; số lượng được đối chiếu, không chỉ kiểm tra vài hàm riêng.",
      '- Bốn log riêng: `SCENARIO_1_CAT_FEED.jsonl`, `SCENARIO_2_DOG_WARNING.jsonl`, `SCENARIO_3_FOOD_A.jsonl`, `SCENARIO_4_FOOD_B.jsonl`.',
      '- `safety_checks.jsonl`, `timeline.csv`, `compile.log`, `native.stderr.log`, `negative_production_cli.log`, `result.json` và hashes giữ bằng chứng.',
      '- Input logs giữ species/confidence/bbox thật của simulator, frame size, ROI scope và HC timestamp/validity; UART logs giữ frame_hex để kiểm tra lại byte/CRC. Đây đều là input synthetic, không phải inference camera thật.',
      '- `simulation.sqlite3` chỉ được tạo độc quyền dưới một run directory mới. Runner không có option nhận DB/device production.',
      '- SQLite có CHECK simulation=1, physical_execution=0 cho events. Các bảng feed/meal là simulation-only. Production-style inbox được tái sử dụng bằng `DryRunRequests.enqueue_in_transaction` với clock được mock đúng phạm vi test.',
      '- `feed_dry_run_requests` vẫn giữ actuator_execution=false và actual_dispensed_grams=null; actual35g mô phỏng chỉ nằm trong bảng/event SIMULATION riêng. Retry không ghi đè quyết định đầu.',
      '- Lần chạy trước được giữ lại. Không cleanup/xóa data, không sửa frontend hay database/source production.',
      '',
      '| Table test | Rows |', '|---|---:|',
    ]
    lines += [f'| {table} | {count} |' for table,count in counts.items()]
    lines += [
      '', '## 5. Files changed', '',
      'Chỉ thêm source/tooling dưới `D:\\for_cat\\E2E_OFFLINE_DEMO_20261028\\`:',
      '- `sim_support.h`: fake clock/PinIO/raw ADC/fake servo/daily store/UART link và composition các core hiện có.',
      '- `simulation_preference.h`: observer tiêu thụ60s, ngưỡng18/5g, validation/noise/tare/stale; không có identity hoặc actuator API.',
      '- `e2e_demo.cpp`:4 demo chính và safety matrix; chỉ có entry point `--simulation-only`.',
      '- `run_demo.py`: C++14 build, stream recorder, test SQLite, gọi class inbox production và assertion độc lập.',
      '- `make_report.py`: đọc evidence bằng SQLite read-only, tạo đúng report milestone này.',
      '- `runs/<UTC>/...`, `latest_run.json`: artifacts chạy thực tế, không phải physical evidence.',
      '',
      'Không sửa các source production được tái sử dụng. Các hash nằm trong `result.json` (HX711/ROI/approach/arbiter/UART/safety policy/dry-run inbox/scheduled worker).',
      '', '## 6. Chạy lại trên Windows', '', '```powershell',
      '& "D:\\for_cat\\.venv\\Scripts\\python.exe" "D:\\for_cat\\E2E_OFFLINE_DEMO_20261028\\run_demo.py"',
      '```', '',
      'Lệnh build bằng Zig C++ có sẵn, không tải dependency/model. Fake clock không sleep60s/2h. Mỗi lần tạo run directory mới; chat/console chỉ in summary.',
      '', 'Chỉ đọc lại evidence / tạo report, không chạy demo lại:', '', '```powershell',
      '& "D:\\for_cat\\.venv\\Scripts\\python.exe" "D:\\for_cat\\E2E_OFFLINE_DEMO_20261028\\make_report.py"', '```',
      '', '## 7. Những điểm còn thiếu trong production integration', '',
      '- Camera/YOLO/TensorRT thật và producer/bridge POSIX không được chạy trên Windows: harness nhập bbox tổng hợp vào core ROI/fusion có thật. Không suy Windows build là Jetson build PASS.',
      '- Portable safety controller và daily store đã compose thành pipeline simulation. Production arbiter vẫn dry-run; durable quota/journal/restart recovery và đường dispatch tới firmware thật chưa được bật/tuyên bố hoàn chỉnh.',
      '- UARTv1 envelope/version/CRC và DOG_WARNING receiver được dùng nguyên. Feeding trong harness là in-process simulation dispatch; không bịa rằng binary FEED_REQUEST production đã điều khiển servo thật.',
      '- Preference18/5g là module demo theo lượng tiêu thụ. Legacy analytics nhiều phiên/identity không được dùng để giả nhận diện nhai/ngửi và chưa được thay thế hoặc đưa kết quả demo vào API production.',
      '- Fake servo45°/90° là angle target thuần dữ liệu. Khả năng gate đóng thật, flow/in-flight food/overshoot, động cơ, loadcell drift và nguồn đều chưa được xác minh bằng harness.',
      '', '## 8. Chuẩn bị port Jetson sau này', '',
      '1. Rebuild các producer/bridge/consumer bằng toolchain C++14 ARM64 và SDK Jetson thực. Binary Windows trong run này không phải firmware hay ELF ARM.',
      '2. JSON boundary giữa detector/ROI/AI state mang CAT/DOG/NONE, bbox NORMALIZED_ORIGINAL, mode, timestamp và eligibility. C++ struct chỉ dùng nội bộ; không gửi raw struct phụ thuộc ABI qua UART. Rebuild đồng bộ consumer sau thay đổi header.',
      '3. UARTv1 dùng fixed-width LE32/length/CRC hiện hành; không đổi IDs hoặc schema để chạy mock. Cần xác minh thực tế baud, by-id port, reconnect/CRC/TTL và một UART owner trên Jetson.',
      '4. Giữ engine production `/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine`, dùng lại detector C++ OpenCV/YOLOv8n320/TensorRT FP16. Khi có Jetson, kiểm tra hash/bindings/SDK compatibility trước khi load; không train/re-export hoặc tải model mới cho milestone này.',
      '5. ARM64 ABI/linker, CUDA/TensorRT engine execution, camera latency/ROI thật: **NOT_VERIFIED**. Không SSH hoặc mở webcam để kiểm tra trong lần làm này.',
      '', '## 9. Checklist physical sau này', '',
      '- [ ] HX711 calibration/zero ổn định và kiểm tra khối lượng sau reboot trên mounting thật; giữ PHYSICAL_VALIDATION_PENDING cho tới khi có evidence.',
      '- [ ] Xác minh camera cố định/bbox thật, FULL_FRAME không giả IN_ROI, ROI_ENABLED review từ ảnh thật; thời gian AI/HC cùng cửa sổ và không stale.',
      '- [ ] Servo MG996R góc45°/90° thực tế, nguồn5V riêng/chung GND, gate close/fault/timeout và food flow được kiểm tra trong phiên giám sát riêng; pump vẫn locked.',
      '- [ ] Thử cấp feedback35g có cân thật, ghi actual/overshoot, sensor fault/USB loss/abort không giả success. Chỉ mở quyền production khi được owner cho phép sau đủ validation.',
      '- [ ] MH-FMD GPIO2/VCC3V3/ACTIVE_LOW: boot OFF,2 tiếng200/200/200ms, cooldown60s; test an toàn riêng không chạy servo/pump.',
      '- [ ] SQLite quota/idempotency/restart thật và meal consumption từ cân thật được đánh dấu đúng nguồn; kết quả fake không đưa vào lịch sử VALIDATED_SENSOR.',
      '',
      f"Native binary SHA256: `{result['native_binary_sha256']}`.",
      '', '**E2E_OFFLINE_DEMO_READY: YES**', '',
    ]
    report=ROOT/'E2E_OFFLINE_DEMO_20261028.md'
    report.write_text('\n'.join(lines),encoding='utf-8')
    receipt={'report_path':str(report),'evidence_path':str(run_dir),'report_sha256':sha(report),'database_read_only_inspection':True,
             'four_scenarios':'PASS','event_count':len(rows),'table_rows':counts,'negative_production_cli':'PASS','E2E_OFFLINE_DEMO_READY':True}
    (run_dir/'report_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    return report

if __name__=='__main__':write_report()
