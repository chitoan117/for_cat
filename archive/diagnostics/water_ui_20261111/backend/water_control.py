"""Explicit, expiring water-control intents. Never persists an auto-enable policy."""
from contextlib import closing
from pathlib import Path
import json,math,sqlite3,time,uuid

ACTIVE=('PENDING','DISPATCHED')
def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def connect(path,timeout=.3):return sqlite3.connect(str(path),timeout=timeout)
def init(path):
    with closing(connect(path)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS water_requests(id TEXT PRIMARY KEY,action TEXT NOT NULL,status TEXT NOT NULL,boot TEXT NOT NULL,requested REAL NOT NULL,dispatched REAL,note TEXT)')
        db.commit()
def startup_off(path):
    init(path)
    with closing(connect(path)) as db:
        db.execute("UPDATE water_requests SET status='CANCELLED',note='Khởi động lại; cần xác nhận lại.' WHERE status IN ('PENDING','DISPATCHED')")
        db.execute('INSERT INTO water_requests VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,'DISABLE','PENDING',boot_id(),time.monotonic(),None,'Mặc định tắt khi khởi động.'))
        db.commit()
def view(path):
    init(path)
    with closing(connect(path)) as db:
        table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='esp32_latest'").fetchone()
        row=db.execute('SELECT body FROM esp32_latest WHERE id=1').fetchone() if table else None
        req=db.execute('SELECT id,action,status,note FROM water_requests ORDER BY requested DESC LIMIT 1').fetchone()
    data=json.loads(row[0]) if row else {};stamp=data.get('updated_monotonic_ms')
    fresh=(data.get('host_boot_id')==boot_id() and type(stamp) in (int,float) and 0<=time.monotonic()*1000-stamp<2500)
    fc=(data.get('telemetry') or {}).get('fc_live') or {}
    supported=fresh and type(fc.get('pump_auto_enabled')) is bool and type(fc.get('pump_test_running')) is bool
    us=(data.get('telemetry') or {}).get('ultrasonic') or {}
    def distance(key):
        s=us.get(key) or {};x=s.get('distance_cm')
        return x if fresh and s.get('valid') is True and type(x) in (int,float) and math.isfinite(x) else None
    return {'fresh':fresh,'supported':supported,'enabled':fc.get('pump_auto_enabled') if supported else None,
        'running':(fc.get('pump_auto_running') is True or fc.get('pump_test_running') is True) if supported else None,
        'fault':fc.get('pump_auto_fault') if supported else None,'reason':fc.get('pump_reason') if supported else None,
        'd1_cm':distance('JSN_SR04T_1'),'d2_cm':distance('JSN_SR04T_2'),
        'can_enable':supported and fc.get('pump_test_running') is False and distance('JSN_SR04T_1') is not None and fc.get('bench_state') in ('READY','MASS OK GATE?','CAT FAULT*'),
        'request':dict(zip(('id','action','status','note'),req)) if req else None,
        'default_enabled':False}
def enqueue(path,identifier,action):
    init(path)
    with closing(connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        existing=db.execute('SELECT action FROM water_requests WHERE id=?',(identifier,)).fetchone()
        if existing:
            if existing[0]!=action:raise ValueError('ID đã dùng cho thao tác khác.')
            db.commit();return
        if action=='DISABLE':
            db.execute("UPDATE water_requests SET status='CANCELLED',note='Đã có yêu cầu tắt.' WHERE status IN ('PENDING','DISPATCHED')")
        elif db.execute("SELECT 1 FROM water_requests WHERE status IN ('PENDING','DISPATCHED')").fetchone():
            raise ValueError('Đang xử lý lệnh trước, hãy chờ trạng thái cập nhật.')
        db.execute('INSERT INTO water_requests VALUES(?,?,?,?,?,?,?)',(identifier,action,'PENDING',boot_id(),time.monotonic(),None,''))
        db.commit()

class Dispatcher:
    def __init__(self,bridge):self.bridge=bridge;self.connected=0;self.device_boot=None
    def on_connect(self,ser):
        # OFF is issued before any enabled request can be processed.
        ser.write(b'pump_auto off\npump_off\n');self.connected=time.monotonic()
        with closing(connect(self.bridge.db_path,.05)) as db:
            db.execute("UPDATE water_requests SET status='CANCELLED',note='UART kết nối lại; cần xác nhận lại.' WHERE action='ENABLE' AND status IN ('PENDING','DISPATCHED')")
            db.commit()
    def tick(self,ser):
        now=time.monotonic()
        with closing(connect(self.bridge.db_path,.05)) as db:
            db.execute('BEGIN IMMEDIATE')
            device_boot=self.bridge.last_status.get('boot')
            if device_boot is not None and self.device_boot is not None and device_boot!=self.device_boot:
                ser.write(b'pump_auto off\npump_off\n');self.connected=now
                db.execute("UPDATE water_requests SET status='CANCELLED',note='ESP32 khởi động lại; cần xác nhận lại.' WHERE action='ENABLE' AND status IN ('PENDING','DISPATCHED')")
            if device_boot is not None:self.device_boot=device_boot
            row=db.execute("SELECT id,action,status,boot,requested,dispatched FROM water_requests WHERE status IN ('PENDING','DISPATCHED') ORDER BY CASE action WHEN 'DISABLE' THEN 0 ELSE 1 END,requested LIMIT 1").fetchone()
            if not row:db.commit();return
            ident,action,state,boot,requested,dispatched=row
            def finish(status,note):db.execute('UPDATE water_requests SET status=?,note=? WHERE id=?',(status,note,ident))
            if boot!=self.bridge.boot_id or (action=='ENABLE' and (requested<self.connected or now-requested>8)):
                if state=='DISPATCHED' and action=='ENABLE':ser.write(b'pump_auto off\npump_off\n')
                finish('EXPIRED','Yêu cầu hết hạn; cần xác nhận lại.');db.commit();return
            msg=self.bridge.last_status
            fresh=0<=now-self.bridge.status_received_mono<2.5
            if state=='DISPATCHED':
                new=fresh and self.bridge.status_received_mono>dispatched
                enabled=msg.get('pump_auto_enabled');test=msg.get('pump_test_running')
                applied=new and ((action=='ENABLE' and enabled is True) or (action=='DISABLE' and enabled is False and test is False))
                if applied:finish('APPLIED','Thiết bị đã xác nhận.');db.commit();return
                if now-dispatched>4:
                    ser.write(b'pump_auto off\npump_off\n')
                    finish('TIMEOUT','Chưa xác nhận được trên ESP32; đã gửi lệnh tắt.');db.commit();return
                db.commit();return
            if action=='ENABLE':
                if not fresh or type(msg.get('pump_auto_enabled')) is not bool:
                    finish('REJECTED','Chưa có trạng thái mới từ ESP32.');db.commit();return
                if msg.get('pump_auto_enabled') is True:
                    finish('APPLIED','Chế độ nước đã bật.');db.commit();return
            db.execute("UPDATE water_requests SET status='DISPATCHED',dispatched=? WHERE id=?",(now,ident));db.commit()
            # Mark before sending: a process crash never replays an enable.
            command=b'pump_reset\npump_driver_verified\npump_auto on\n' if action=='ENABLE' else b'pump_auto off\npump_off\n'
            ser.write(command)
