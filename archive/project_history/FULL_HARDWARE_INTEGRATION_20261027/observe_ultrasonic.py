"""Supervised common ultrasonic harness. No actuator/NVS/flash commands.

One diagnostic serial owner during selection, otherwise existing RX bridge only.
All measurements are REAL; synthetic unit fixtures never enter this runner's DB.
"""
import argparse
import asyncio
import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import subprocess
import time

SENSORS={
 'hc1':('HC_SR04_1',12,13,'CAT_APPROACH'),
 'jsn1':('JSN_SR04T_1',14,15,'WATER_LEVEL'),
 'hc2':('HC_SR04_2',16,17,'TBD'),
 'jsn2':('JSN_SR04T_2',18,10,'TBD')}
COMMANDS={f'ultra-select {key} CONFIRM' for key in SENSORS}|{'ultra-off CONFIRM','ultra-multiplex CONFIRM'}|{f'ultra-guard {value} CONFIRM' for value in (60,80,100)}

def command_bytes(command):
    if command not in COMMANDS:raise ValueError('Command outside fixed sensor-only whitelist')
    return (command+'\n').encode('ascii')

class LineBuffer:
    """Bounded split-packet CR/LF framing; discard oversize line, then recover."""
    def __init__(self):self.pending=bytearray();self.dropping=False;self.oversized=0
    def feed(self,chunk):
        result=[]
        for byte in chunk:
            if byte in (10,13):
                if not self.dropping and self.pending:result.append(bytes(self.pending))
                self.pending.clear();self.dropping=False
            elif not self.dropping:
                if len(self.pending)<4096:self.pending.append(byte)
                else:self.pending.clear();self.dropping=True;self.oversized+=1
        return result

def summarize(rows):
    values=[r['distance_cm'] for r in rows if r.get('valid') is True and r.get('state')=='HEALTHY'
            and r.get('timeout') is not True and r.get('stale') is not True
            and type(r.get('distance_cm')) in (int,float) and math.isfinite(r['distance_cm']) and 0<r['distance_cm']<=400]
    jumps=[abs(b-a) for a,b in zip(values,values[1:])]
    ages=[r['sample_age_ms'] for r in rows if type(r.get('sample_age_ms')) in (int,float)]
    stamps=[r['last_update'] for r in rows if r.get('last_update') is not None]
    return {'count':len(rows),'valid_count':len(values),'valid_rate':len(values)/len(rows) if rows else 0,
      'timeout_count':sum(r.get('timeout') is True for r in rows),'stale_count':sum(r.get('stale') is True for r in rows),
      'timeout_counter_delta':rows[-1].get('timeout_count',0)-rows[0].get('timeout_count',0) if rows else None,
      'min_cm':min(values) if values else None,'max_cm':max(values) if values else None,
      'mean_cm':statistics.mean(values) if values else None,'median_cm':statistics.median(values) if values else None,
      'stddev_cm':statistics.pstdev(values) if values else None,'spread_cm':max(values)-min(values) if values else None,
      'max_jump_cm':max(jumps,default=0) if values else None,'distinct_distances':len(set(values)),
      'unique_updates':len(set(stamps)),'max_age_ms':max(ages,default=None)}

def assess(key,stats,target):
    """Explicit preliminary bench sanity, not calibrated accuracy/auto thresholds."""
    if stats['count']<20 or stats['unique_updates']<20:
        return {'result':'DIAGNOSED','action_required':True,'reason':'INSUFFICIENT_INDEPENDENT_UPDATES'}
    if stats['valid_count']==0:
        suspect=key.startswith('jsn') and target<30
        return {'result':'DIAGNOSED','action_required':True,
          'reason':'RANGE_LIMIT_SUSPECTED' if suspect else 'NO_VALID_ECHO',
          'range_limit_suspected':suspect,'cause_proven':False,
          'other_possible_causes':['target alignment','supply/wiring','echo acquisition']}
    band=(max(1,target-5),target+5);limit=max(5,target*.25)
    if stats['valid_rate']<=.5:
        reason='VALID_RATE_NOT_MAJORITY'
    elif not band[0]<=stats['median_cm']<=band[1]:
        reason='TARGET_RANGE_OR_ALIGNMENT_REQUIRES_REVIEW'
    elif stats['max_jump_cm']>limit or stats['spread_cm']>limit or stats['stddev_cm']>max(2,target*.1):
        reason='UNSTABLE_OR_LARGE_JUMPS'
    elif stats['distinct_distances']<2:
        reason='CONSTANT_READING_NEEDS_MOVEMENT_PROOF'
    else:
        return {'result':'PHYSICAL_PASS','action_required':False,
          'scope':'BASIC_RANGING_AT_OWNER_APPROXIMATE_TARGET_NOT_ACCURACY_CERTIFICATE',
          'sanity_band_cm':list(band),'jitter_limit_cm':limit}
    return {'result':'DIAGNOSED','action_required':True,'reason':reason,'sanity_band_cm':list(band),
      'range_limit_suspected':key.startswith('jsn') and target<30,'cause_proven':False}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def json_stream(text):
    decoder=json.JSONDecoder();position=0;values=[]
    while position<len(text):
        while position<len(text) and text[position].isspace():position+=1
        if position==len(text):break
        value,position=decoder.raw_decode(text,position);values.append(value)
    return values

def hx_fit_review(points):
    by_mass={p['mass_g']:p for p in points if p.get('phase')=='fit'}
    zero=by_mass.get(0);rows=[]
    for mass,p in sorted(by_mass.items()):
        stats=p['stats'];row={'reference_g':mass,'point_id':p['point_id'],'stats':stats,
          'delta_from_zero_counts':stats['mean_raw']-zero['stats']['mean_raw'] if zero else None}
        if mass and zero:
            z=zero['stats'];row['raw_ranges_separated']=stats['raw_max_all']<z['raw_min_all'] or stats['raw_min_all']>z['raw_max_all']
            noise=max(z['spread_counts'],stats['spread_counts'],1)
            row['response_to_spread_ratio']=abs(row['delta_from_zero_counts'])/noise
        rows.append(row)
    loaded=[r for r in rows if r['reference_g']>0]
    response=bool(loaded) and all(r.get('raw_ranges_separated') and r['response_to_spread_ratio']>1 for r in loaded)
    return {'fit_points':rows,'basic_raw_load_response_observed':response,
      'raw_direction':'DECREASING_WITH_ADDED_LOAD' if loaded and all(r['delta_from_zero_counts']<0 for r in loaded) else 'INCREASING_WITH_ADDED_LOAD' if loaded and all(r['delta_from_zero_counts']>0 for r in loaded) else 'UNKNOWN',
      'missing_fit_masses_g':[m for m in (0,5,10,20,30,35) if m not in by_mass],
      'calibration_state':'NOT_CALIBRATED','grams':None,'factor_computed':False,'stable_in_grams':'UNKNOWN'}

class DiagnosticPort:
    """Bounded raw POSIX UART handoff, mirroring bridge settings, no DTR/RTS IOCTL."""
    def __init__(self,device):
        import os,fcntl,termios
        self.os=os;self.fcntl=fcntl;self.termios=termios
        self.device=device;self.txfd=None
        self.trace={'device':device,'read_calls':0,'ready_calls':0,'read_bytes':0,'opened_monotonic':time.monotonic()}
        self.fd=os.open(device,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
        try:
            fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.ioctl(self.fd,termios.TIOCEXCL)
            cfg=termios.tcgetattr(self.fd);self.trace['initial_termios']=repr(cfg);cfg[0]=cfg[1]=cfg[3]=0
            cfg[2]=(cfg[2]&~(termios.CSIZE|termios.PARENB|termios.CSTOPB|termios.HUPCL|termios.CRTSCTS))|termios.CS8|termios.CLOCAL|termios.CREAD
            cfg[4]=cfg[5]=termios.B115200;cfg[6][termios.VMIN]=0;cfg[6][termios.VTIME]=0
            termios.tcsetattr(self.fd,termios.TCSANOW,cfg)
            self.trace['configured_termios']=repr(termios.tcgetattr(self.fd))
        except Exception:os.close(self.fd);raise
    def __enter__(self):return self
    def __exit__(self,*unused):
        try:
            if self.txfd is not None:self.os.close(self.txfd)
            self.fcntl.ioctl(self.fd,self.termios.TIOCNXCL)
        finally:self.os.close(self.fd)
    def fileno(self):return self.fd
    @property
    def in_waiting(self):
        import array
        value=array.array('i',[0]);self.fcntl.ioctl(self.fd,self.termios.FIONREAD,value,True);return value[0]
    def read(self,count):
        import select
        self.trace['read_calls']+=1
        if not select.select([self.fd],[],[],.1)[0]:return b''
        self.trace['ready_calls']+=1
        try:
            value=self.os.read(self.fd,count);self.trace['read_bytes']+=len(value);return value
        except BlockingIOError:return b''
    def write(self,value):
        import select
        if self.txfd is None:
            # Initial RX open matches canonical bridge exactly. A same-process
            # TX-only descriptor is opened only after safe frames were received.
            self.fcntl.ioctl(self.fd,self.termios.TIOCNXCL)
            try:self.txfd=self.os.open(self.device,self.os.O_WRONLY|self.os.O_NOCTTY|self.os.O_NONBLOCK|self.os.O_CLOEXEC)
            finally:self.fcntl.ioctl(self.fd,self.termios.TIOCEXCL)
        # All caller commands are checked against the fixed whitelist first.
        sent=0;deadline=time.monotonic()+1
        while sent<len(value):
            if time.monotonic()>deadline:raise TimeoutError('UART_WRITE_BUDGET')
            if select.select([],[self.txfd],[],.1)[1]:sent+=self.os.write(self.txfd,value[sent:])
        return sent
    def flush(self):pass  # ACK reception is the bounded proof of transmission.

class Observer:
    def __init__(self,evidence):
        self.evidence=Path(evidence);assert self.evidence.is_dir()
        self.out=self.evidence/'fast_track_ultrasonic';self.out.mkdir(exist_ok=True)
        self.run=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.ledger_path=self.out/'STATUS.json'
        self.ledger=json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {'sensors':{},'scheduler':{'result':'NOT_TESTED'}}
        self.active_guard_ms=self.ledger.get('current_guard_ms',80)
        self.control_step=0
        self.journal=[]
    def save(self,name,data):
        path=self.out/(self.run+'_'+name+'.json')
        with path.open('x') as f:f.write(json.dumps(data,indent=2))
        return path
    def manifest(self):
        self.ledger_path.write_text(json.dumps(self.ledger,indent=2))
        (self.out/'manifest_sha256.json').write_text(json.dumps({p.name:sha(p) for p in self.out.iterdir() if p.is_file() and p.name!='manifest_sha256.json'},indent=2))
    def get(self,path):
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=6) as r:return json.load(r)
    def safe(self,state):
        if state.get('data_source')!='REAL' or state.get('esp32',{}).get('connected') is not True:raise RuntimeError('REAL_LINK_NOT_READY')
        safety=state['safety']
        if safety.get('actuator_outputs_enabled')!=0 or any(safety.get(k) is not False for k in ('auto_feed','auto_water','servo_armed','pump_armed','actuator_execution')):raise RuntimeError('SAFETY_CHANGED_STOP')
        self.identities(state['ultrasonic'])
    def identities(self,rows):
        if set(rows)!={s[0] for s in SENSORS.values()}:raise RuntimeError('CHANNEL_SET_MISMATCH')
        for key,(ident,trig,echo,role) in SENSORS.items():
            s=rows[ident]
            if (s.get('trigger_gpio'),s.get('echo_gpio'),s.get('role'))!=(trig,echo,role):raise RuntimeError('PIN_OR_ROLE_MISMATCH_'+key)
    def mask(self,state,keys):
        self.safe(state);wanted={SENSORS[key][0] for key in keys}
        for ident,s in state['ultrasonic'].items():
            if s.get('firmware_supported') is not True:raise RuntimeError('FLASH_REQUIRED')
            if s['enabled']!=(ident in wanted):raise RuntimeError('ACQUISITION_MASK_MISMATCH')
            if ident not in wanted and s['distance_cm'] is not None:raise RuntimeError('DISABLED_CHANNEL_HAS_CURRENT_VALUE')
    def adopt_hc1(self):
        near=self.evidence/'hc1_target_20cm_passive_20261027T045529082502Z'
        far=self.evidence/'hc1_after_sensor_5v_20261027T043932670884Z'
        existing=self.ledger['sensors'].get('hc1',{})
        if existing.get('result')=='PHYSICAL_PASS' and existing.get('source_evidence')==[str(near),str(far)]:return
        n=json.loads((near/'samples.json').read_text());f=json.loads((far/'samples.json').read_text())
        ns=summarize(n);fs=summarize(f);decision=assess('hc1',ns,20)
        if decision['result']!='PHYSICAL_PASS' or fs['valid_count']<20 or not ns['max_cm']<fs['min_cm']:raise RuntimeError('HC1_REUSE_EVIDENCE_INSUFFICIENT')
        record={'sensor':'HC_SR04_1','timestamp':utc(),'target_cm':20,'stats':ns,'baseline_40cm':fs,
          'mean_delta_from_40_cm':ns['mean_cm']-fs['mean_cm'],**decision,
          'source_evidence':[str(near),str(far)],'no_remeasurement':True,
          'limitation':'Resets recorded between captures; not a soak/restart-reliability PASS'}
        self.save('hc1_existing_evidence_assessment',record);self.ledger['sensors']['hc1']=record;self.manifest()
    def select(self,keys,guard=None):
        """Only fixed select commands; RX bridge stopped for exclusive handoff."""
        from serial.tools import list_ports
        before=self.get('/api/status');self.safe(before)
        ports=[p for p in list_ports.comports() if p.vid==0x1a86 and p.pid==0x55d3 and p.serial_number=='5C85066678']
        if len(ports)!=1:raise RuntimeError('ESP32_IDENTITY_NOT_UNIQUE')
        device=ports[0].device;frames=[];lines=[];framer=LineBuffer();tx=[];io_trace={}
        commands=[f'ultra-select {key} CONFIRM' for key in keys]
        if not keys:commands=['ultra-off CONFIRM']
        if guard is not None:commands.insert(0,f'ultra-guard {guard} CONFIRM')
        if len(keys)==4:commands.append('ultra-multiplex CONFIRM')
        self.control_step+=1
        control_tag='control_'+('-'.join(keys))+f'_g{guard}_step{self.control_step}'
        logname=self.run+'_'+control_tag
        subprocess.run(['systemctl','--user','stop','for-cat-esp32-bridge.service'],check=True,timeout=20)
        try:
            if subprocess.run(['fuser',device],capture_output=True).returncode!=1:raise RuntimeError('SERIAL_STILL_OWNED')
            with (self.out/(logname+'.bin')).open('xb') as raw:
                with DiagnosticPort(device) as p:
                    io_trace=p.trace
                    def receive(seconds,ack=None):
                        end=time.monotonic()+seconds
                        while time.monotonic()<end:
                            chunk=p.read(min(4096,max(1,p.in_waiting)))
                            if not chunk:continue
                            raw.write(chunk)
                            if raw.tell()>262144:raise RuntimeError('RAW_BUDGET')
                            for line in framer.feed(chunk):
                                text=line.decode('utf-8','replace');lines.append(text)
                                if line.startswith(b'{'):
                                    try:f=json.loads(line)
                                    except ValueError:continue
                                    if f['mode']!='diag_current_hardware' or f.get('ultrasonic_schema_version')!=1 or f.get('rtc_type')!='NONE':raise RuntimeError('UNSUPPORTED_FIRMWARE')
                                    if f['actuator_outputs_enabled']!=0 or f['physical_pump_on'] is not False or any(f['current_hardware'][k] is not False for k in ('servo_armed','pump_armed','auto_feed','auto_water')):raise RuntimeError('WIRE_SAFETY_CHANGED')
                                    self.identities(f['ultrasonic']);frames.append(f)
                                if ack and text.startswith(ack):return True
                        return False
                    baseline_deadline=time.monotonic()+7
                    while len(frames)<2 and time.monotonic()<baseline_deadline:
                        receive(.4)
                    if len(frames)<2:raise RuntimeError('NO_SAFE_BASELINE_FRAMES')
                    if guard is not None and frames[-1].get('ultrasonic_guard_ms') not in (60,80,100):raise RuntimeError('MANUAL_FLASH_REQUIRED_FOR_RUNTIME_GUARD_CONTROL')
                    for command in commands:
                        ack='ULTRA_OFF' if command=='ultra-off CONFIRM' else 'ULTRA_SEQUENTIAL_REVIEWED' if command=='ultra-multiplex CONFIRM' else f'ULTRA_GUARD_MS {guard} RUNTIME_ONLY' if command.startswith('ultra-guard ') else 'ULTRA_SINGLE_ACQUISITION_ENABLED_NOT_PHYSICAL_PASS'
                        accepted=False
                        for attempt in range(3):
                            p.write(command_bytes(command));p.flush();tx.append({'at':utc(),'command':command,'attempt':attempt+1})
                            if receive(1.4,ack):accepted=True;break
                        if not accepted:raise RuntimeError('SELECT_ACK_MISSING_'+command)
                    receive(1.5)
                    expected={SENSORS[key][0] for key in keys}
                    if not frames or {ident for ident,row in frames[-1]['ultrasonic'].items() if row['enabled']}!=expected:raise RuntimeError('WIRE_SELECTION_MASK_MISMATCH')
                    self.active_guard_ms=frames[-1].get('ultrasonic_guard_ms',80)
                    if guard is not None and self.active_guard_ms!=guard:raise RuntimeError('GUARD_TELEMETRY_MISMATCH')
                    self.ledger['current_guard_ms']=self.active_guard_ms
        finally:
            subprocess.run(['systemctl','--user','start','for-cat-esp32-bridge.service'],check=True,timeout=20)
            self.save(control_tag,{'before_uptime_ms':before['esp32']['monotonic_ms'],
              'last_raw_uptime_ms':frames[-1]['monotonic_ms'] if frames else None,'tx':tx,'raw_frames':frames,'lines':lines,
              'actuator_commands_sent':False,'serial_exclusive':True,'control_lines_manipulated':False,
              'adapter':'POSIX_RAW_NO_DTR_RTS','io_trace':io_trace,'remaining_buffer_bytes':len(framer.pending),'oversized_lines':framer.oversized,
              'reset_observed':frames[-1]['monotonic_ms']<before['esp32']['monotonic_ms'] if frames else None})
        for _ in range(30):
            try:self.mask(self.get('/api/status'),keys);return
            except RuntimeError:time.sleep(.5)
        raise RuntimeError('BRIDGE_SELECTION_DID_NOT_RECOVER')
    def collect(self,keys,count,warmup,phase=''):
        time.sleep(warmup);rows={key:[] for key in keys};seen={key:set() for key in keys};states=[]
        deadline=time.monotonic()+max(60,count*3)
        while time.monotonic()<deadline and any(len(v)<count for v in rows.values()):
            s=self.get('/api/status');self.mask(s,keys);states.append(s)
            for key in keys:
                row=s['ultrasonic'][SENSORS[key][0]];stamp=row['last_update']
                if len(rows[key])<count and stamp is not None and stamp not in seen[key]:
                    seen[key].add(stamp);rows[key].append({'observed_at':s['observed_at'],**row})
            if any(len(v)<count for v in rows.values()):time.sleep(1.05)
        async def ws_frames():
            import websockets
            async with websockets.connect('ws://127.0.0.1:8000/api/ws/state',open_timeout=8,max_size=131072) as ws:
                return [json.loads(await asyncio.wait_for(ws.recv(),8)) for _ in range(3)]
        ws=asyncio.run(ws_frames())
        for s in ws:self.mask(s,keys)
        worker=self.get('/api/meal-plans/worker')['worker']
        if not worker['enabled'] or not worker['running'] or worker['last_error'] is not None or worker['actual_dispensed_grams'] is not None:raise RuntimeError('WORKER_OR_ACTUAL_STATE_CHANGED')
        pid=int(subprocess.check_output(['systemctl','--user','show','for-cat-esp32-bridge','-p','MainPID','--value']))
        owner=subprocess.run(['fuser','/dev/ttyACM0'],capture_output=True)
        if [int(p) for p in owner.stdout.split()]!=[pid]:raise RuntimeError('SERIAL_OWNER_MISMATCH')
        suffix=('_'+phase) if phase else ''
        tag='-'.join(keys);self.save(tag+'_raw_api'+suffix,{'states':states,'websocket_frames':ws})
        for key,values in rows.items():
            fields=['observed_at','sensor_id','state','distance_cm','valid','timeout','stale','sample_age_ms','last_update','timeout_count']
            with (self.out/(self.run+'_'+key+('_scheduler' if len(keys)>1 else '')+suffix+'.csv')).open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(values)
        return rows,states
    def single(self,key,args):
        state=self.get('/api/status')
        if args.guard_ms is not None:self.select([key],args.guard_ms)
        else:
            try:self.mask(state,[key])
            except RuntimeError:self.select([key])
        rows,states=self.collect([key],args.samples,args.warmup);stats=summarize(rows[key]);decision=assess(key,stats,args.target_cm)
        counters=[s['esp32']['counters'] for s in states]
        if counters and counters[-1]['device_reboots']!=counters[0]['device_reboots']:decision={'result':'DIAGNOSED','action_required':True,'reason':'MCU_REBOOT_DURING_CAPTURE'}
        record={'timestamp':utc(),'sensor':SENSORS[key][0],'target_cm':args.target_cm,'target_source':'OWNER_FIXED_TARGET_NOT_INDEPENDENTLY_SURVEYED_PER_SENSOR',
          'stats':stats,'samples':rows[key],**decision,'safety':states[-1]['safety'] if states else None,
          'guard_ms':self.active_guard_ms,'other_channels_disabled':True,'config':SENSORS[key]}
        path=self.save(key+'_single',record);record['evidence']=str(path);self.ledger['sensors'][key]=record;self.manifest();return record
    def scheduler(self,args):
        if any(self.ledger['sensors'].get(key,{}).get('result')!='PHYSICAL_PASS' for key in SENSORS):raise RuntimeError('ALL_SINGLE_CHANNEL_RESULTS_REQUIRED')
        self.select(list(SENSORS),args.guard_ms);rows,states=self.collect(list(SENSORS),args.samples,args.warmup,phase=f'g{self.active_guard_ms}')
        stats={key:summarize(values) for key,values in rows.items()};checks={}
        for key,values in stats.items():
            record=self.ledger['sensors'][key];base=record['stats']
            expected=base['median_cm']+(args.target_cm-record['target_cm'])
            shift=abs(values['median_cm']-expected) if values['median_cm'] is not None else None
            checks[key]=values['count']>=20 and values['valid_rate']>=max(.75,base['valid_rate']-.1) and values['max_age_ms'] is not None and values['max_age_ms']<=2000 and shift is not None and shift<=max(3,abs(expected)*.15) and values['stddev_cm']<=max(2,base['stddev_cm']*2+.3) and values['max_jump_cm']<=max(5,args.target_cm*.25)
        correlations={}
        for i,key in enumerate(SENSORS):
            for other in list(SENSORS)[i+1:]:
                pairs=[(a['distance_cm'],b['distance_cm']) for a,b in zip(rows[key],rows[other]) if a['valid'] and b['valid']]
                if len(pairs)>=3:
                    a,b=zip(*pairs);ma,mb=statistics.mean(a),statistics.mean(b)
                    den=math.sqrt(sum((v-ma)**2 for v in a)*sum((v-mb)**2 for v in b))
                    correlations[key+'_'+other]=sum((x-ma)*(y-mb) for x,y in pairs)/den if den else None
        result={'timestamp':utc(),'result':'RUNTIME_PASS' if all(checks.values()) else 'DIAGNOSED','checks':checks,'stats':stats,
          'guard_ms_tested':[self.active_guard_ms],'guard_ms':self.active_guard_ms,
          'smallest_stable_guard':'REQUIRES_BOUNDED_SWEEP_COMPARISON',
          'target_reference':'Shared flat target translated to current nominal target without rotation; baseline per-sensor offsets retained for sanity only',
          'pairwise_noise_correlation':correlations,'correlation_limitation':'Common stationary target correlation alone cannot prove acoustic contamination',
          'cpu_loop_timing':'NO_MCU_CPU_METRIC_EXPOSED; freshness/cadence only checked','safety':states[-1]['safety']}
        self.save(f'scheduler_g{self.active_guard_ms}',result);self.ledger['scheduler']=result;self.manifest();return result
    def check_flash(self,relative):
        folder=(self.evidence/relative).resolve()
        if not folder.is_relative_to(self.evidence.resolve()):raise RuntimeError('FLASH_RECEIPT_OUTSIDE_MILESTONE')
        receipt=json.loads((folder/'receipt.json').read_text());release=folder.parent
        manifest=json.loads((release/'release_manifest.json').read_text())
        if receipt['status']!='RUNTIME_PASS' or not receipt['nvs_unchanged'] or len(receipt['writes'])!=1 or receipt['writes'][0]['offset']!='0x10000':raise RuntimeError('FLASH_RECEIPT_NOT_VERIFIED')
        if receipt['writes'][0]['image_sha256']!=manifest['firmware']['firmware.bin']:raise RuntimeError('FLASH_IMAGE_HASH_MISMATCH')
        if len(receipt['commands'])!=7 or any(c['exit'] for c in receipt['commands']):raise RuntimeError('FLASH_COMMAND_FAILED')
        if sha(folder/'nvs_before.bin')!=sha(folder/'nvs_after.bin') or sha(folder/'nvs_after.bin')!=receipt['nvs_sha256']:raise RuntimeError('NVS_MISMATCH')
        if sha(release/'host_release/firmware/firmware.bin')!=manifest['firmware']['firmware.bin']:raise RuntimeError('RELEASE_IMAGE_CHANGED')
        s=self.get('/api/status');self.safe(s)
        if any(row['enabled'] is not False or row['state']!='DISABLED' or row['distance_cm'] is not None for row in s['ultrasonic'].values()):raise RuntimeError('POST_FLASH_CHANNELS_NOT_DISABLED')
        if any(row['firmware_supported'] is not True for row in s['ultrasonic'].values()):raise RuntimeError('POST_FLASH_EXTENSION_MISSING')
        worker=self.get('/api/meal-plans/worker')['worker']
        if not worker['running'] or not worker['enabled'] or worker['last_error'] is not None or worker['actual_dispensed_grams'] is not None:raise RuntimeError('POST_FLASH_WORKER_SAFETY')
        result={'result':'RUNTIME_PASS','receipt':str(folder/'receipt.json'),'image_sha256':manifest['firmware']['firmware.bin'],'nvs_unchanged':True,
          'all_four_disabled':True,'safety':s['safety'],'serial_opened':False,'commands_sent':[]}
        self.save('guard_flash_verified',result);self.ledger['guard_tuning_release']={'status':'FLASH_VERIFIED','image_sha256':result['image_sha256'],'receipt':result['receipt']};self.manifest();return result
    def audit(self):
        state=self.get('/api/status');self.safe(state)
        raw=self.get('/api/v1/esp32/status');worker=self.get('/api/meal-plans/worker')['worker']
        expected=json.loads((self.evidence/'release_manifest.json').read_text())
        root=Path('/home/toan/for_cat')
        data_updates=self.ledger.get('validated_data_updates',{})
        source={name:sha(root/name)==(data_updates.get(name,meta['after']) if name in ('config/hardware_current.json','docs/CURRENT_PROJECT_STATE.md') else meta['after']) for name,meta in expected['files'].items()}
        if not all(source.values()):raise RuntimeError('DEPLOYED_SOURCE_CHANGED')
        if raw['serial_tx_enabled'] is not False or worker['mode']!='DRY_RUN_ONLY' or worker['last_error'] is not None:raise RuntimeError('BASELINE_CHANGED')
        if sha(root/'.git/index')!=json.loads((self.evidence/'preflight_summary.json').read_text())['index_sha256']:raise RuntimeError('INDEX_CHANGED')
        self.save('host_audit',{'at':utc(),'schema':state['ultrasonic_schema_version'],'source_sha_matches':source,'worker':worker,
          'serial_tx_enabled':raw['serial_tx_enabled'],'safety':state['safety'],'actuator_execution':False})
    def finish_milestone(self):
        self.mask(self.get('/api/status'),[])
        scheduler=self.ledger['scheduler']
        if scheduler.get('result')!='RUNTIME_PASS' or len(scheduler.get('bounded_sweep',[]))!=3:raise RuntimeError('BOUNDED_SWEEP_NOT_COMPLETE')
        if any(self.ledger['sensors'].get(k,{}).get('result')!='PHYSICAL_PASS' for k in SENSORS):raise RuntimeError('SINGLE_CHANNEL_PROOF_MISSING')
        root=Path('/home/toan/for_cat');config_path=root/'config/hardware_current.json';doc_path=root/'docs/CURRENT_PROJECT_STATE.md'
        config=json.loads(config_path.read_text());old_doc=doc_path.read_text()
        proofs={}
        for key,(ident,_,_,_) in SENSORS.items():
            record=self.ledger['sensors'][key]
            refs=record.get('source_evidence') or [record['evidence']]
            for ref in refs:
                if not Path(ref).exists():raise RuntimeError('PHYSICAL_EVIDENCE_PATH_MISSING')
            proofs[ident]={'result':'PHYSICAL_PASS','scope':record['scope'],'target_cm':record['target_cm'],'evidence':refs,'timestamp':record.get('timestamp')}
            config['ultrasonic_inventory'][ident].update(physical_status='PHYSICAL_PASS',physical_scope=record['scope'],physical_evidence=refs)
        chosen=scheduler['chosen_guard_ms']
        config['four_channel_integration'].update(flash_required=False,guard_ms=chosen,scheduler_result='RUNTIME_PASS',
            scheduler_scope=scheduler['scope'],single_channel_physical='PHYSICAL_PASS',physical_validation='PHYSICAL_PASS',physical_validation_scope='BASIC_RANGING_ONLY_NOT_ACCURACY_OR_SOAK',
            physical_evidence=str(self.ledger_path),firmware_sha256=self.ledger.get('guard_tuning_release',{}).get('image_sha256'))
        self.save('hardware_config_before_physical_closeout',json.loads(config_path.read_text()))
        self.save('current_document_before_physical_closeout',{'text':old_doc})
        text=json.dumps(config,indent=2)+'\n'
        if len(text.encode())>65536:raise RuntimeError('CONFIG_READ_BOUND_EXCEEDED')
        tmp=config_path.with_name(config_path.name+'.physical_tmp');tmp.write_text(text);tmp.replace(config_path)
        heading='## Physical ultrasonic fast-track 2026-10-27 — basic ranging and bounded scheduler window\n\n'
        body=('HC1/JSN1/HC2/JSN2 have external PHYSICAL_PASS evidence for basic ranging at owner-positioned approximate20/40cm targets; not metrology, geometry or soak certification.\n'
          'Guard sweep60/80/100ms completed once each;80ms was the smallest tested window meeting declared criteria. JSN1 still had22/24 valid reports at80ms and earlier windows were worse; intermittent timeouts are not eliminated. No unconditional reliability claim.\n'
          'Guard80ms is RAM-selected and also firmware reset default. Acquisition is now ALL DISABLED to isolate HX711 work. Runtime telemetry physical_verification is not an external test certificate; the canonical inventory and evidence ledger hold the dated test facts.\n'
          'HX711 passive raw acquisition RUNTIME_PASS, load response and fresh gram calibration NOT_TESTED/NOT_CALIBRATED; no active model, gramsnull. Servo/pump/AUTO remain blocked, outputs0 and actual_dispensed=null.\n'
          'Evidence: `'+str(self.ledger_path)+'`. Old wiring/calibration/NOT_TESTED sections below are retained as historical checkpoints.\n\n')
        title,sep,rest=old_doc.partition('\n');new_doc=title+'\n\n'+heading+body+rest.lstrip('\n')
        tmp=doc_path.with_name(doc_path.name+'.physical_tmp');tmp.write_text(new_doc);tmp.replace(doc_path)
        self.ledger['validated_data_updates']={name:sha(root/name) for name in ('config/hardware_current.json','docs/CURRENT_PROJECT_STATE.md')}
        backend_log=(self.evidence/'backend_post.log').read_text()
        import re
        backend_count=int(re.search(r'(\d+) passed',backend_log).group(1))
        for args in (['git','diff','--check'],['git','diff','--cached','--check']):
            p=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            if p.returncode:raise RuntimeError('PHYSICAL_DOC_DIFF_CHECK_FAILED '+p.stdout.decode())
        result={'result':'RUNTIME_PASS','timestamp':utc(),'sensor_proofs':proofs,'scheduler_guard_ms':chosen,
          'scope':'BASIC_SENSOR_PHYSICAL_PASS_AND_BOUNDED_SCHEDULER_WINDOW_NOT_SOAK',
          'regression':{'backend':backend_count,'flutter':63,'js':14,'note':'Latest full Flutter/JS checks in session transcript; application source unchanged; backend log in milestone'},
          'current_acquisition':'ALL_DISABLED_FOR_HX711','next_action':'Remove reference weights/food from normally mounted load-cell tray; do not touch during capture',
          'hx711_calibration':'NOT_CALIBRATED','actuator_execution':False,'actual_dispensed_grams':None}
        self.save('milestone_closeout',result);self.ledger['milestone']=result;self.manifest();return result
    def hx_readiness(self,args):
        rows=[];seen=set();deadline=time.monotonic()+max(60,args.samples*3)
        while len(rows)<args.samples and time.monotonic()<deadline:
            state=self.get('/api/status');self.safe(state);w=state['weight']
            if w.get('grams') is not None or w.get('calibration_state')!='NOT_CALIBRATED':raise RuntimeError('UNEXPECTED_HX_CALIBRATION_STATE')
            stamp=(state['esp32']['monotonic_ms'],w.get('sampled_at'))
            if w.get('raw_available') is True and type(w.get('raw_counts')) in (int,float) and stamp not in seen:
                seen.add(stamp);rows.append({'observed_at':state['observed_at'],**w})
            if len(rows)<args.samples:time.sleep(1.05)
        values=[r['raw_counts'] for r in rows]
        nonsaturated=bool(values) and all(math.isfinite(v) and -8388608<v<8388607 for v in values)
        result={'result':'RUNTIME_PASS' if len(values)>=20 and nonsaturated and len(set(values))>=2 else 'DIAGNOSED',
          'scope':'PASSIVE_RAW_ACQUISITION_ONLY_NOT_LOAD_RESPONSE','count':len(values),
          'raw_min':min(values) if values else None,'raw_max':max(values) if values else None,
          'raw_mean':statistics.mean(values) if values else None,'raw_stddev':statistics.pstdev(values) if values else None,
          'distinct_raw':len(set(values)),'no_saturation':nonsaturated,'grams':None,'calibration_state':'NOT_CALIBRATED',
          'load_response':'NOT_TESTED','reference_mass':'UNKNOWN','physical_status':'NOT_TESTED',
          'calibration_metadata':self.get('/api/hx711/calibration'),'samples':rows,'serial_opened':False,'commands_sent':[]}
        self.save('hx_readiness',result);self.ledger['hx711']={k:v for k,v in result.items() if k not in ('samples','calibration_metadata')};self.manifest()
        return {k:v for k,v in result.items() if k not in ('samples','calibration_metadata')}
    def prepare_hx_session(self):
        self.mask(self.get('/api/status'),[])
        before=self.get('/api/hx711/calibration')
        if before.get('active') is not None:raise RuntimeError('ACTIVE_HX_MODEL_EXISTS_REVIEW_BEFORE_STARTING_NEW_SESSION')
        hx=self.get('/api/hx711/status')
        if hx.get('actuator_execution') is not False or hx.get('actual_dispensed_grams') is not None:raise RuntimeError('HX_ACTUATION_SAFETY_CHANGED')
        existing=self.ledger.get('hx711_session',{})
        if existing.get('session_id') and existing['session_id']==(before.get('latest_session') or {}).get('session_id'):
            return {**existing,'reused_existing_session':True}
        self.save('hx_metadata_before_new_session',before)
        import sqlite3
        root=Path('/home/toan/for_cat');database=root/'jetson/data/events.db'
        backup=self.evidence/'backup'/('events_before_hx_session_'+self.run+'.db')
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=10) as source,sqlite3.connect(backup) as dest:
            source.backup(dest,pages=256,sleep=.05)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('HX_BACKUP_INTEGRITY_FAILED')
        command=['/home/toan/for_cat/.venv/jetson-integration/bin/python',str(root/'jetson/tools/hx711_calibration.py'),
          'new','--evidence-dir',str(self.out),'--load-cell-capacity-g','5000']
        p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
        (self.out/(self.run+'_hx_session_create.log')).write_bytes(p.stdout)
        if p.returncode:raise RuntimeError('EXISTING_HX_TOOL_SESSION_CREATE_FAILED '+p.stdout.decode())
        session=json.loads(p.stdout);sid=session['session_id']
        if session['state']!='AWAITING_ZERO':raise RuntimeError('UNEXPECTED_NEW_HX_STATE')
        after=self.get('/api/hx711/calibration')
        if (after.get('latest_session') or {}).get('session_id')!=sid or after.get('active') is not None:raise RuntimeError('HX_SESSION_API_MISMATCH')
        result={'result':'SOFTWARE_READY','milestone':'CALIBRATION_STARTED_SOFTWARE_PREPARATION_ONLY','session_id':sid,'state':session['state'],
          'zero_reference_confirmed':False,'physical_points_captured':0,'grams':None,'physical_calibration':'NOT_CALIBRATED',
          'backup':str(backup),'backup_sha256':sha(backup),'existing_tool':command[1],'timestamp':utc(),
          'next_action':'Operator remove reference weights/food from normally mounted tray; await explicit empty-tray confirmation',
          'serial_opened':False,'nvs_writes':False,'actuator_execution':False,'actual_dispensed_grams':None}
        self.save('hx_session_prepared',result);self.ledger['hx711_session']=result;self.manifest();return result
    def capture_hx_reference(self,args):
        if not args.operator_confirmed:raise RuntimeError('EXPLICIT_OPERATOR_REFERENCE_CONFIRMATION_REQUIRED')
        state=self.get('/api/status');self.mask(state,[])
        session_record=self.ledger.get('hx711_session',{});sid=session_record.get('session_id')
        if not sid:raise RuntimeError('NO_PREPARED_HX_SESSION')
        before=self.get('/api/hx711/calibration');session=before.get('latest_session') or {}
        if session.get('session_id')!=sid:raise RuntimeError('HX_SESSION_CHANGED_REVIEW_BEFORE_CAPTURE')
        if args.hx_phase=='fit' and before.get('active') is not None:raise RuntimeError('UNEXPECTED_ACTIVE_MODEL_DURING_FIT')
        mass=args.hx_capture
        if args.hx_phase=='fit':
            previous=[p for p in before.get('point_summaries',[]) if p['phase']=='fit' and p['mass_g']==mass]
            if previous:return {'result':'SOFTWARE_READY','reason':'FIT_POINT_ALREADY_RECORDED_NO_AUTOMATIC_RECAPTURE','point_id':previous[-1]['point_id'],'session_id':sid,'reference_g':mass}
        confirmation={'at':utc(),'source':'USER_EXPLICIT_REFERENCE_PLACEMENT_CONFIRMATION','phase':args.hx_phase,'reference_g':mass,
          'session_id':sid,'ultrasonic_acquisition':'ALL_DISABLED','safety_before':state['safety']}
        self.save(f'hx_{args.hx_phase}_{mass:g}g_operator_confirmation',confirmation)
        root=Path('/home/toan/for_cat')
        command=['/home/toan/for_cat/.venv/jetson-integration/bin/python',str(root/'jetson/tools/hx711_calibration.py'),
          'capture','--session',sid,'--phase',args.hx_phase,'--mass-g',str(mass),'--seconds','30','--settle-seconds','5']
        p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        log=self.out/(self.run+f'_hx_{args.hx_phase}_{mass:g}g_capture.log');log.write_bytes(p.stdout)
        messages=json_stream(p.stdout.decode('utf-8','replace'))
        if p.returncode:
            result={'result':'DIAGNOSED','session_id':sid,'reference_g':mass,'tool_messages':messages,'log':str(log),
              'physical_calibration':'NOT_CALIBRATED','actuator_execution':False,'actual_dispensed_grams':None}
            self.save(f'hx_{args.hx_phase}_{mass:g}g_failed',result);return result
        point=next((m for m in reversed(messages) if isinstance(m,dict) and 'point_id' in m),None)
        if point is None:raise RuntimeError('EXISTING_CALIBRATION_TOOL_RETURNED_NO_POINT')
        raw_path=Path(point['evidence']);sidecar=raw_path.with_name(raw_path.name+'.sha256')
        if sha(raw_path)!=sidecar.read_text().strip():raise RuntimeError('HX_RAW_EVIDENCE_CHECKSUM_MISMATCH')
        point_path=raw_path.parent/(point['point_id']+'.point.json');full=json.loads(point_path.read_text())
        if full['mass_g']!=mass or full['session_id']!=sid:raise RuntimeError('HX_POINT_IDENTITY_MISMATCH')
        stats=point['stats']
        if stats['inlier_count']<25 or stats['span_seconds']<25:raise RuntimeError('HX_REFERENCE_CAPTURE_TOO_SHORT')
        with (self.out/(self.run+f'_hx_{args.hx_phase}_{mass:g}g_samples.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['device_ms','observed_at','raw','age_seconds'],extrasaction='ignore');writer.writeheader();writer.writerows(full['samples'])
        after=self.get('/api/hx711/calibration');final=self.get('/api/status');self.mask(final,[])
        if args.hx_phase in ('fit','verify') and (after.get('active') is not None or final['weight']['grams'] is not None):raise RuntimeError('UNEXPECTED_GRAM_AUTHORITY_DURING_REFERENCE_CAPTURE')
        result={'result':'RUNTIME_PASS','scope':'PHYSICAL_REFERENCE_RAW_CAPTURE_NOT_CALIBRATION_PASS',
          'session_id':sid,'phase':args.hx_phase,'reference_g':mass,'point_id':point['point_id'],'stats':stats,
          'tare_candidate_counts':point.get('tare_candidate_counts'),'measured_grams':point.get('grams'),
          'candidate_grams':point.get('candidate_grams'),'stable':point.get('stable'),'error_grams':None,'error_percent':None,
          'state':point['state'],'raw_evidence':str(raw_path),'raw_sha256':sha(raw_path),'point_evidence':str(point_path),
          'safety_after':final['safety'],'actuator_execution':False,'actual_dispensed_grams':None,'nvs_writes':False}
        if point.get('candidate_grams') is not None:
            candidate=point['candidate_grams'];criteria=session['criteria'];quality=point.get('candidate_quality') or {}
            tolerance=criteria['zero_error_g'] if mass==0 else max(criteria['absolute_error_g'],mass*criteria['relative_error_fraction'])
            result.update(candidate_quality=quality,error_grams=candidate-mass,
              error_percent=(candidate-mass)/mass*100 if mass else None,tolerance_g=tolerance,
              independent_point_passed=quality.get('stable') is True and abs(candidate-mass)<=tolerance,
              point_assessment_scope='CANDIDATE_CHECK_ONLY_NOT_ACTIVATION_OR_PERSISTENCE_PASS')
        self.save(f'hx_{args.hx_phase}_{mass:g}g_recorded',result)
        session_record.update(state=point['state'],zero_reference_confirmed=mass==0 or session_record.get('zero_reference_confirmed',False),
          physical_points_captured=len([v for v in after.get('point_summaries',[]) if v['phase']=='fit']),last_point_id=point['point_id'])
        self.ledger['hx711_session']=session_record;self.manifest();return result
    def review_hx_points(self):
        state=self.get('/api/status');self.mask(state,[])
        data=self.get('/api/hx711/calibration');sid=self.ledger.get('hx711_session',{}).get('session_id')
        if (data.get('latest_session') or {}).get('session_id')!=sid or data.get('active') is not None:raise RuntimeError('HX_REVIEW_SESSION_OR_AUTHORITY_CHANGED')
        result=hx_fit_review(data.get('point_summaries',[]));result.update(session_id=sid,timestamp=utc(),safety=state['safety'],actuator_execution=False,actual_dispensed_grams=None)
        self.save('hx_fit_review',result);self.ledger['hx711_fit_review']=result;self.manifest();return result
    def fit_hx_model(self):
        state=self.get('/api/status');self.mask(state,[])
        before=self.get('/api/hx711/calibration');session=before.get('latest_session') or {}
        sid=self.ledger.get('hx711_session',{}).get('session_id')
        if not sid or session.get('session_id')!=sid or before.get('active') is not None:raise RuntimeError('HX_FIT_SESSION_OR_AUTHORITY_CHANGED')
        masses={p['mass_g'] for p in before.get('point_summaries',[]) if p['phase']=='fit'}
        if not {0,5,10,20,30,35}.issubset(masses):raise RuntimeError('FIT_REFERENCE_SET_INCOMPLETE')
        existing=session.get('candidate')
        if existing is None:
            root=Path('/home/toan/for_cat');command=['/home/toan/for_cat/.venv/jetson-integration/bin/python',str(root/'jetson/tools/hx711_calibration.py'),'fit','--session',sid]
            p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
            log=self.out/(self.run+'_hx_model_fit.log');log.write_bytes(p.stdout)
            messages=json_stream(p.stdout.decode('utf-8','replace'))
            if p.returncode:
                result={'result':'DIAGNOSED','session_id':sid,'tool_messages':messages,'log':str(log),'physical_calibration':'NOT_CALIBRATED'}
                self.save('hx_fit_model_failed',result);return result
            session=messages[-1]
        model=session['candidate'];after=self.get('/api/hx711/calibration')
        if after.get('active') is not None or (after.get('latest_session') or {}).get('candidate_digest')!=session['candidate_digest']:raise RuntimeError('HX_FIT_API_DIGEST_MISMATCH')
        final=self.get('/api/status');self.mask(final,[])
        if final['weight']['grams'] is not None:raise RuntimeError('UNEXPECTED_GRAM_PROMOTION_AFTER_FIT')
        results=model['fit_results']
        if len(results)!=6 or any(not row['stable'] or abs(row['error_g'])>row['tolerance_g'] for row in results):raise RuntimeError('MODEL_FIT_QUALITY_NOT_ACCEPTABLE')
        with (self.out/(self.run+'_hx_fit_results.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=sorted({k for row in results for k in row}));writer.writeheader();writer.writerows(results)
        result={'result':'SOFTWARE_READY','scope':'SIX_POINT_FIT_ONLY_INDEPENDENT_VERIFY_REQUIRED','session_id':sid,'state':session['state'],
          'tare_offset_counts':model['tare_offset_counts'],'counts_per_gram':model['counts_per_gram'],'grams_per_count':model['grams_per_count'],
          'candidate_digest':session['candidate_digest'],'fit_results':results,'max_abs_fit_error_g':max(abs(row['error_g']) for row in results),
          'validation_passed':model['validation_passed'],'active_model':False,'canonical_grams':None,
          'physical_calibration':'NOT_CALIBRATED','safety':final['safety'],'actuator_execution':False,'actual_dispensed_grams':None,
          'next_action':'Remove all reference weights for an independent verify0g; do not retare or refit'}
        self.save('hx_model_fit_ready',result);self.ledger['hx711_model_fit']=result
        self.ledger['hx711_session'].update(state=session['state'],candidate_digest=session['candidate_digest']);self.manifest();return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sensor',choices=[*SENSORS,'all']);group.add_argument('--sequence',nargs='+',choices=[*SENSORS,'all']);group.add_argument('--status',action='store_true');group.add_argument('--hx-readiness',action='store_true');group.add_argument('--check-flash',metavar='RELATIVE_RECEIPT_DIR');group.add_argument('--off',action='store_true');group.add_argument('--finish-milestone',action='store_true');group.add_argument('--prepare-hx-session',action='store_true');group.add_argument('--hx-capture',type=float,choices=(0,5,10,20,30,35),metavar='GRAMS');group.add_argument('--hx-review',action='store_true');group.add_argument('--hx-fit',action='store_true')
    parser.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--samples',type=int,default=24);parser.add_argument('--target-cm',type=float)
    parser.add_argument('--warmup',type=float,default=3);parser.add_argument('--adopt-hc1',action='store_true')
    parser.add_argument('--guard-ms',type=int,choices=(60,80,100));parser.add_argument('--guard-sweep',action='store_true')
    parser.add_argument('--hx-phase',choices=('fit','verify','persistence'),default='fit');parser.add_argument('--operator-confirmed',action='store_true')
    args=parser.parse_args()
    if not args.status and not args.check_flash and not args.off and not args.finish_milestone and not args.prepare_hx_session and not args.hx_review and not args.hx_fit and args.hx_capture is None and (not 20<=args.samples<=100 or not 2.5<=args.warmup<=10 or (not args.hx_readiness and (args.target_cm is None or not 1<=args.target_cm<=400))):parser.error('Bounded sample/target/warmup limits; explicit target required')
    if args.status:
        observer=Observer(args.evidence)
        guard_summary=observer.evidence/'guard_tuning_release/software_summary.json'
        if guard_summary.is_file() and observer.ledger.get('guard_tuning_release',{}).get('status')!='FLASH_VERIFIED':
            meta=json.loads(guard_summary.read_text())
            observer.ledger['guard_tuning_release']={'status':meta['status'],'image_sha256':meta['image_sha256'],
              'release':meta['release'],'flash_performed_by_agent':False,'manual_command':meta['manual_command']}
        observer.manifest()
        compact={**observer.ledger,'sensors':{key:{k:v for k,v in record.items() if k!='samples'} for key,record in observer.ledger['sensors'].items()}}
        print(json.dumps(compact,indent=2));return
    if args.guard_sweep and args.sensor!='all':parser.error('Guard sweep requires --sensor all')
    observer=Observer(args.evidence);report={'status':'BLOCKED','at':utc(),'results':[],'actuator_commands_sent':False}
    try:
        if args.adopt_hc1:observer.adopt_hc1()
        observer.audit()
        if args.hx_fit:
            result=observer.fit_hx_model();report['results'].append(result);report['status']=result['result'];return
        if args.hx_review:
            report['results'].append(observer.review_hx_points());report['status']='RUNTIME_PASS';return
        if args.hx_capture is not None:
            result=observer.capture_hx_reference(args);report['results'].append(result);report['status']=result['result'];return
        if args.prepare_hx_session:
            report['results'].append(observer.prepare_hx_session());report['status']='SOFTWARE_READY';return
        if args.finish_milestone:
            report['results'].append(observer.finish_milestone());report['status']='RUNTIME_PASS';return
        if args.off:
            observer.select([]);state=observer.get('/api/status');observer.mask(state,[])
            report.update(status='RUNTIME_PASS',acquisition='ALL_DISABLED_FOR_HX711',safety=state['safety']);return
        if args.check_flash:
            report['results'].append(observer.check_flash(args.check_flash));report['status']='RUNTIME_PASS';return
        if args.hx_readiness:
            report['results'].append(observer.hx_readiness(args));report['status']=report['results'][-1]['result'];return
        if args.guard_sweep:
            for guard in (60,80,100):
                args.guard_ms=guard;report['results'].append(observer.scheduler(args))
            stable=[r['guard_ms'] for r in report['results'] if r['result']=='RUNTIME_PASS']
            if stable:
                chosen=min(stable);observer.select(list(SENSORS),chosen)
                report.update(status='RUNTIME_PASS',chosen_guard_ms=chosen,scope='SMALLEST_TESTED_WINDOW_PASS_NOT_LONG_TERM_SOAK')
                observer.ledger['scheduler']={'result':'RUNTIME_PASS','chosen_guard_ms':chosen,'bounded_sweep':report['results'],'scope':report['scope']}
            else:
                report.update(status='ACTION_REQUIRED',reason='NO_STABLE_GUARD_IN_BOUNDED_60_80_100_SWEEP')
            return
        for key in args.sequence or [args.sensor]:
            result=observer.scheduler(args) if key=='all' else observer.single(key,args)
            report['results'].append({k:v for k,v in result.items() if k!='samples'})
            if result.get('action_required') or result['result']=='DIAGNOSED':
                report.update(status='ACTION_REQUIRED',blocked_sensor=key,reason=result.get('reason','SCHEDULER_REVIEW_REQUIRED'));break
        else:report['status']='RUNTIME_PASS'
    except Exception as error:
        report.update(status='ACTION_REQUIRED',reason=str(error))
    finally:
        observer.save('run_report',report);observer.manifest();print(json.dumps(report,indent=2))

if __name__=='__main__':main()
