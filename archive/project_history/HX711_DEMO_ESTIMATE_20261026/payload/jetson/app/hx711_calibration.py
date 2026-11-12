"""Host-side physical-reference calibration. No serial, feed, NVS or actuator API."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
import uuid
from datetime import datetime, timezone

MASSES = (0, 5, 10, 20, 30, 35)
CRITERIA = {'absolute_error_g': .1, 'relative_error_fraction': .01, 'zero_error_g': .1,
            'stable_spread_g': .2, 'stable_stddev_g': .05, 'stable_drift_g': .1,
            'minimum_samples': 25, 'minimum_span_s': 25, 'max_outlier_fraction': .1,
            'live_window_samples': 10, 'live_minimum_span_s': 8}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def checksum(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def binding(bridge):
    if bridge.get('usb_serial') != '5C85066678' or bridge.get('usb_vid') != '1a86' or bridge.get('usb_pid') != '55d3':
        raise ValueError('HX device identity is not the previously verified ESP32')
    if bridge.get('telemetry', {}).get('mode') != 'diag_current_hardware':
        raise ValueError('unexpected firmware diagnostic mode')
    return {'usb_serial': bridge['usb_serial'], 'usb_vid': bridge['usb_vid'], 'usb_pid': bridge['usb_pid'],
            'dout_gpio': 4, 'sck_gpio': 5, 'mode': 'diag_current_hardware',
            'adc_configuration': 'CHANNEL_A_GAIN128_FROM_AUDITED_FIRMWARE_SOURCE',
            'authority': 'JETSON_SQLITE_PHYSICAL_REFERENCE_V1'}


def safe_bridge(bridge):
    if bridge.get('telemetry_usable_now') is not True or bridge.get('health') != 'ESP32_CONNECTED' or bridge.get('unsafe_telemetry_latched') is not False:
        raise ValueError('fresh usable REAL telemetry required')
    flags = bridge.get('telemetry', {}).get('safety', {})
    if not all(flags.get(k) is False for k in ('servo_armed', 'pump_armed', 'auto_feed', 'auto_water', 'actuator_execution')) or type(flags.get('actuator_outputs_enabled')) is not int or flags['actuator_outputs_enabled'] != 0:
        raise ValueError('actuator safety state unknown or unsafe')
    hx = bridge.get('telemetry', {}).get('sensors', {}).get('hx711', {})
    raw = hx.get('raw_counts')
    if hx.get('raw_available') is not True or not number(raw) or not -8388608 < raw < 8388607 or int(raw) != raw:
        raise ValueError('HX raw missing, invalid or ADC saturated')
    return raw


def raw_statistics(samples, criteria=CRITERIA):
    if len(samples) < 2 or any(not number(s.get('raw')) or not -8388608 < s['raw'] < 8388607 or int(s['raw'])!=s['raw'] for s in samples):
        raise ValueError('multiple finite non-railed raw samples required')
    ticks = [s['device_ms'] for s in samples]
    if any(type(t) is not int for t in ticks) or any(b <= a for a,b in zip(ticks,ticks[1:])):
        raise ValueError('samples must be distinct, increasing device reports')
    values = [s['raw'] for s in samples]
    center = statistics.median(values)
    mad = statistics.median(abs(v-center) for v in values)
    threshold = max(6*1.4826*mad, 1)
    retained = [i for i,v in enumerate(values) if abs(v-center) <= threshold]
    rejected = [i for i in range(len(values)) if i not in retained]
    if len(retained) < 2 or len(rejected)/len(values) > criteria['max_outlier_fraction']:
        raise ValueError('too many outliers; do not hide an unstable capture')
    if any(b==a+1 for a,b in zip(rejected,rejected[1:])):
        raise ValueError('contiguous outliers suggest movement; repeat the capture')
    good = [values[i] for i in retained]
    half = max(1, len(good)//2)
    span = (ticks[-1]-ticks[0])/1000
    return {'samples':len(samples), 'span_seconds':span, 'mean_raw':statistics.mean(good),
            'median_raw':center, 'raw_min_all':min(values), 'raw_max_all':max(values),
            'spread_counts':max(good)-min(good), 'stddev_counts':statistics.pstdev(good),
            'drift_counts':abs(statistics.mean(good[:half])-statistics.mean(good[-half:])),
            'rejected_indices':rejected, 'inlier_count':len(good)}


def point_quality(stats, factor, criteria):
    scale = abs(factor)
    spread, noise, drift = (stats[key]*scale for key in ('spread_counts','stddev_counts','drift_counts'))
    return {'spread_g':spread, 'stddev_g':noise, 'drift_g':drift,
            'stable': spread <= criteria['stable_spread_g'] and noise <= criteria['stable_stddev_g'] and drift <= criteria['stable_drift_g']}


def fit_model(points, criteria):
    by_mass = {p['mass_g']:p for p in points}
    if any(m not in by_mass for m in MASSES):
        raise ValueError('fit needs separate0/5/10/20/30/35g captures')
    ordered = [by_mass[m] for m in MASSES]
    if len({p['host_boot_id'] for p in ordered}) != 1 or max(p['boot_estimate_ms'] for p in ordered)-min(p['boot_estimate_ms'] for p in ordered)>5000:
        raise ValueError('restart between fit points; repeat a consistent fit sequence')
    for p in ordered:
        if p['stats']['inlier_count'] < criteria['minimum_samples'] or p['stats']['span_seconds'] < criteria['minimum_span_s']:
            raise ValueError('fit window too short')
    offset = ordered[0]['stats']['mean_raw']
    slope = sum(m*(by_mass[m]['stats']['mean_raw']-offset) for m in MASSES[1:])/sum(m*m for m in MASSES[1:])
    if not number(slope) or slope == 0:
        raise ValueError('no measurable load response')
    factor = 1/slope
    if abs(factor) > criteria['absolute_error_g']/2:
        raise ValueError('raw quantization too coarse for proposed gram tolerance')
    sign = 1 if slope>0 else -1
    means = [p['stats']['mean_raw'] for p in ordered]
    if any(sign*(b-a)<=0 for a,b in zip(means,means[1:])):
        raise ValueError('load response is not monotonic')
    results=[]
    for p in ordered:
        mass=p['mass_g'];predicted=(p['stats']['mean_raw']-offset)*factor
        tolerance=criteria['zero_error_g'] if mass==0 else max(criteria['absolute_error_g'],mass*criteria['relative_error_fraction'])
        quality=point_quality(p['stats'],factor,criteria)
        if not quality['stable'] or abs(predicted-mass)>tolerance:
            raise ValueError('fit/noise does not meet proposed tolerance at '+str(mass)+'g')
        results.append({'mass_g':mass,'candidate_grams':predicted,'error_g':predicted-mass,'tolerance_g':tolerance,**quality})
    return {'schema_version':'hx711_host_cal_v1','tare_offset_counts':offset,'counts_per_gram':slope,
            'grams_per_count':factor,'range_grams':[0,35],'criteria':criteria,'fit_results':results,
            'fit_point_ids':[p['point_id'] for p in ordered], 'validation_passed':False,
            'fit_host_boot_id':ordered[0]['host_boot_id'],'fit_boot_estimate_ms':ordered[0]['boot_estimate_ms']}


class CalibrationStore:
    def __init__(self,path):self.path=Path(path).resolve()
    def connect(self):return sqlite3.connect(str(self.path),timeout=.5)
    def initialize(self):
        with closing(self.connect()) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS hx711_calibration_sessions(id TEXT PRIMARY KEY,body TEXT NOT NULL);'
                'CREATE TABLE IF NOT EXISTS hx711_calibration_points(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,body TEXT NOT NULL,digest TEXT NOT NULL);'
                'CREATE TABLE IF NOT EXISTS hx711_calibration_active(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,digest TEXT NOT NULL);')
            db.commit()
    def save_session(self,value):
        with closing(self.connect()) as db:
            db.execute('UPDATE hx711_calibration_sessions SET body=? WHERE id=?',(encoded(value),value['session_id']));db.commit()
    def session(self,identifier):
        if not re.fullmatch(r'hxcal_[a-f0-9]{32}',identifier):raise ValueError('invalid session ID')
        with closing(self.connect()) as db:row=db.execute('SELECT body FROM hx711_calibration_sessions WHERE id=?',(identifier,)).fetchone()
        if row is None:raise ValueError('calibration session not found')
        return json.loads(row[0])
    def new(self,device_binding,evidence_dir,capacity_g=None):
        if capacity_g is not None and (not number(capacity_g) or capacity_g<=0):raise ValueError('invalid declared load cell capacity')
        self.initialize();identifier='hxcal_'+uuid.uuid4().hex
        data={'session_id':identifier,'created_at':datetime.now(timezone.utc).isoformat(),'state':'AWAITING_ZERO',
              'binding':device_binding,'criteria':dict(CRITERIA),'candidate':None,'candidate_digest':None,
              'load_cell_capacity_g':capacity_g,'evidence_dir':str(Path(evidence_dir).resolve()),
              'physical_result':'NOT_TESTED','calibration_authority':'JETSON_SQLITE_PHYSICAL_REFERENCE_V1'}
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM hx711_calibration_sessions').fetchone()[0]>=16:raise ValueError('calibration session limit reached')
            db.execute('INSERT INTO hx711_calibration_sessions VALUES(?,?)',(identifier,encoded(data)))
            db.execute('DELETE FROM hx711_calibration_active')  # explicit new tare/calibration invalidates old gram authority
            db.commit()
        return data
    def points(self,identifier):
        with closing(self.connect()) as db:rows=db.execute('SELECT body,digest FROM hx711_calibration_points WHERE session_id=? ORDER BY rowid',(identifier,)).fetchall()
        result=[]
        for body,digest in rows:
            value=json.loads(body)
            if checksum(value)!=digest:raise ValueError('point checksum mismatch')
            result.append(value)
        return result
    def record(self,identifier,phase,mass,samples,context):
        session=self.session(identifier)
        if phase not in ('fit','verify','persistence') or not number(mass) or mass not in MASSES:raise ValueError('invalid calibration phase/reference')
        if phase!='fit' and session['candidate'] is None:raise ValueError('fit candidate first')
        if mass!=0 and not any(p['phase']=='fit' and p['mass_g']==0 for p in self.points(identifier)):raise ValueError('TEST0g first')
        if session['load_cell_capacity_g'] is not None and mass>session['load_cell_capacity_g']:raise ValueError('reference exceeds declared load cell capacity')
        stats=raw_statistics(samples,session['criteria'])
        if stats['inlier_count']<session['criteria']['minimum_samples'] or stats['span_seconds']<session['criteria']['minimum_span_s']:
            raise ValueError('capture requires at least25 unique reports and25s span')
        if context['binding']!=session['binding']:raise ValueError('device binding changed')
        allowed_context={key:context[key] for key in ('binding','host_boot_id','boot_estimate_ms','capture_origin','safety_before','safety_after')}
        for flags in (context['safety_before'],context['safety_after']):
            if not all(flags.get(k) is False for k in ('servo_armed','pump_armed','auto_feed','auto_water','actuator_execution')) or type(flags.get('actuator_outputs_enabled')) is not int or flags['actuator_outputs_enabled']!=0:raise ValueError('unsafe capture provenance')
        if not isinstance(context['host_boot_id'],str) or not context['host_boot_id'] or not number(context['boot_estimate_ms']):raise ValueError('invalid capture provenance')
        if phase=='persistence':
            active=self.active()
            if active is None or active['calibration_id']!=identifier:raise ValueError('activate valid calibration before persistence capture')
        point={'point_id':uuid.uuid4().hex,'session_id':identifier,'phase':phase,'mass_g':mass,
               'operator_declared_reference':True,'samples':samples,'stats':stats,**allowed_context,
               'candidate_digest':session['candidate_digest'],'captured_at':datetime.now(timezone.utc).isoformat()}
        point['round_id']=session.get(phase+'_round') if phase!='fit' else None
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM hx711_calibration_points').fetchone()[0]>=256:raise ValueError('point ledger full')
            db.execute('INSERT INTO hx711_calibration_points VALUES(?,?,?,?)',(point['point_id'],identifier,encoded(point),checksum(point)))
            if phase=='fit':
                session.update(candidate=None,candidate_digest=None,state='COLLECTING_FIT',physical_result='PHYSICAL_CALIBRATION_IN_PROGRESS')
                db.execute('DELETE FROM hx711_calibration_active')
            db.execute('UPDATE hx711_calibration_sessions SET body=? WHERE id=?',(encoded(session),identifier));db.commit()
        return point
    def fit(self,identifier):
        session=self.session(identifier)
        candidate=fit_model([p for p in self.points(identifier) if p['phase']=='fit'],session['criteria'])
        candidate.update(calibration_id=identifier,binding=session['binding'])
        session.update(candidate=candidate,candidate_digest=checksum(candidate),state='CANDIDATE_PENDING_VALIDATION',
                       verify_round=uuid.uuid4().hex,persistence_round=uuid.uuid4().hex)
        self.save_session(session);return session
    def verify(self,identifier,phase='verify'):
        session=self.session(identifier);model=session['candidate']
        if model is None:raise ValueError('fit candidate first')
        points=[p for p in self.points(identifier) if p['phase']==phase and p['candidate_digest']==session['candidate_digest'] and p.get('round_id')==session.get(phase+'_round')]
        zeros=[p for p in points if p['mass_g']==0];nonzeros=[p for p in points if p['mass_g']!=0]
        required=(0,35) if phase=='persistence' else MASSES
        latest={p['mass_g']:p for p in points}
        if any(m not in latest for m in required) or len(zeros)<2 or not nonzeros or points[0]['mass_g']!=0 or points[-1]['mass_g']!=0:
            raise ValueError('independent validation requires zero, references, and return-to-zero')
        results=[]
        for p in points:
            mass=p['mass_g'];grams=(p['stats']['mean_raw']-model['tare_offset_counts'])*model['grams_per_count']
            tolerance=session['criteria']['zero_error_g'] if mass==0 else max(session['criteria']['absolute_error_g'],mass*session['criteria']['relative_error_fraction'])
            quality=point_quality(p['stats'],model['grams_per_count'],session['criteria'])
            passed=quality['stable'] and abs(grams-mass)<=tolerance
            results.append({'point_id':p['point_id'],'reference_g':mass,'candidate_grams':grams,'error_g':grams-mass,'tolerance_g':tolerance,'passed':passed,**quality})
        if not all(r['passed'] for r in results):raise ValueError('reference validation/stability failed; no activation')
        if phase=='persistence':
            active=self.active()
            if active is None or active['calibration_id']!=identifier:raise ValueError('active calibration missing')
            if not all(p['host_boot_id']!=active['activated_host_boot_id'] or abs(p['boot_estimate_ms']-active['activated_boot_estimate_ms'])>5000 for p in points):
                raise ValueError('no observed ESP32/Jetson restart after activation')
            if any(p['captured_at']<=active['activated_at'] for p in points):raise ValueError('persistence captures predate activation')
        else:
            session.update(state='VALIDATED',validation_results=results);self.save_session(session)
        return results
    def activate(self,identifier,context):
        session=self.session(identifier);results=self.verify(identifier)
        session=self.session(identifier)
        if context['binding']!=session['binding']:raise ValueError('activation device binding changed')
        model={**session['candidate'],'validation_passed':True,'validation_results':results,
               'calibration_state':'CALIBRATED_PENDING_PERSISTENCE','activated_at':datetime.now(timezone.utc).isoformat(),
               'activated_host_boot_id':context['host_boot_id'],'activated_boot_estimate_ms':context['boot_estimate_ms']}
        with closing(self.connect()) as db:
            db.execute('INSERT OR REPLACE INTO hx711_calibration_active VALUES(1,?,?)',(encoded(model),checksum(model)));db.commit()
        session.update(state='CALIBRATED_PENDING_PERSISTENCE',persistence_round=uuid.uuid4().hex);self.save_session(session);return model
    def reset_phase(self,identifier,phase):
        if phase not in ('verify','persistence'):raise ValueError('only validation rounds can be reset')
        session=self.session(identifier)
        if session['candidate'] is None:raise ValueError('fit first')
        active=self.active()
        if phase=='verify' and active is not None:raise ValueError('start a new calibration session before changing validated references')
        if phase=='persistence' and (active is None or active['calibration_id']!=identifier):raise ValueError('activate first')
        session[phase+'_round']=uuid.uuid4().hex
        session['state']='CANDIDATE_PENDING_VALIDATION' if phase=='verify' else 'CALIBRATED_PENDING_PERSISTENCE'
        session['physical_result']='PHYSICAL_CALIBRATION_IN_PROGRESS'
        if phase=='persistence':
            active['calibration_state']='CALIBRATED_PENDING_PERSISTENCE'
            with closing(self.connect()) as db:
                db.execute('UPDATE hx711_calibration_active SET body=?,digest=? WHERE id=1',(encoded(active),checksum(active)));db.commit()
        self.save_session(session)
        return session
    def finish(self,identifier,operator_confirmed=False):
        if operator_confirmed is not True:raise ValueError('operator confirmation of actual physical tests required')
        session=self.session(identifier);results=self.verify(identifier,'persistence')
        active=self.active()
        if active is None or active['calibration_id']!=identifier:raise ValueError('active calibration mismatch')
        active.update(calibration_state='CALIBRATED',persistence_results=results)
        with closing(self.connect()) as db:
            db.execute('UPDATE hx711_calibration_active SET body=?,digest=? WHERE id=1',(encoded(active),checksum(active)));db.commit()
        session.update(state='PHYSICAL_PASS',physical_result='PHYSICAL_PASS',persistence_results=results);self.save_session(session);return session
    def active(self):
        try:
            with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=.1)) as db:
                exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='hx711_calibration_active'").fetchone()
                if not exists:return None
                row=db.execute('SELECT body,digest FROM hx711_calibration_active WHERE id=1').fetchone()
            if not row:return None
            model=json.loads(row[0])
            if checksum(model)!=row[1] or model.get('schema_version')!='hx711_host_cal_v1' or model.get('validation_passed') is not True:raise ValueError('invalid active calibration checksum/state')
            for key in ('tare_offset_counts','grams_per_count','counts_per_gram'):
                if not number(model.get(key)):raise ValueError('invalid active coefficient')
            if not -8388608<model['tare_offset_counts']<8388607 or not 0<abs(model['grams_per_count'])<=CRITERIA['absolute_error_g']/2 or abs(model['grams_per_count']*model['counts_per_gram']-1)>1e-8:
                raise ValueError('invalid active scale/offset')
            if model.get('calibration_state') not in ('CALIBRATED','CALIBRATED_PENDING_PERSISTENCE'):raise ValueError('invalid calibration state')
            if model.get('criteria')!=CRITERIA or model.get('range_grams')!=[0,35] or not re.fullmatch(r'hxcal_[a-f0-9]{32}',model.get('calibration_id','')):raise ValueError('invalid calibration schema/criteria')
            return model
        except sqlite3.OperationalError:
            if not self.path.is_file():return None
            raise
    def demo_candidate(self):
        """Owner-approved display estimate, explicitly NOT active calibration."""
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=.1)) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='hx711_calibration_sessions'").fetchone():return None
            row=db.execute('SELECT body FROM hx711_calibration_sessions ORDER BY rowid DESC LIMIT 1').fetchone()
        if row is None:return None
        session=json.loads(row[0]);approval=session.get('owner_demo_estimate')
        if approval is None or approval.get('enabled') is not True:return None
        budget=approval.get('accepted_error_budget_g')
        if not number(budget) or not 0<budget<=5:raise ValueError('invalid owner demo error budget')
        candidate=session.get('candidate')
        if not isinstance(candidate,dict) or checksum(candidate)!=session.get('candidate_digest') or candidate.get('schema_version')!='hx711_host_cal_v1':raise ValueError('invalid demo candidate integrity')
        if candidate.get('criteria')!=CRITERIA or candidate.get('range_grams')!=[0,35]:raise ValueError('unexpected demo model schema')
        for key in ('tare_offset_counts','grams_per_count','counts_per_gram'):
            if not number(candidate.get(key)):raise ValueError('invalid demo coefficient')
        if not -8388608<candidate['tare_offset_counts']<8388607 or not 0<abs(candidate['grams_per_count'])<=CRITERIA['absolute_error_g']/2 or abs(candidate['grams_per_count']*candidate['counts_per_gram']-1)>1e-8:raise ValueError('invalid demo scale/offset')
        return {**candidate,'owner_demo_estimate':approval}
    def approve_demo_estimate(self,identifier,error_budget_g,owner_confirmed=False):
        if owner_confirmed is not True:raise ValueError('explicit owner acceptance required')
        if not number(error_budget_g) or not 0<error_budget_g<=5:raise ValueError('demo budget must be >0 and <=5g')
        session=self.session(identifier)
        if session.get('candidate') is None or checksum(session['candidate'])!=session['candidate_digest']:raise ValueError('fit candidate required')
        session['owner_demo_estimate']={'enabled':True,'accepted_error_budget_g':error_budget_g,
          'source':'EXPLICIT_OWNER_ACCEPTED_APPROXIMATE_DEMO','approved_at':datetime.now(timezone.utc).isoformat(),
          'requested_future_actual_feed_range_g':[35,40],'physical_feed_range_verified':False,
          'precision_calibration_pass':False,'actuator_execution':False}
        self.save_session(session)
        return session['owner_demo_estimate']
    def status(self):
        active=self.active();latest=None
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,timeout=.1)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='hx711_calibration_sessions'").fetchone():
                row=db.execute('SELECT body FROM hx711_calibration_sessions ORDER BY rowid DESC LIMIT 1').fetchone()
                if row:latest=json.loads(row[0])
        summaries=[] if latest is None else [{key:p[key] for key in ('point_id','phase','mass_g','stats','captured_at')} for p in self.points(latest['session_id'])[-20:]]
        return {'active':active,'latest_session':latest,'point_summaries':summaries,'criteria':dict(CRITERIA),'required_fit_masses_g':list(MASSES),
                'authority':'JETSON_SQLITE_PHYSICAL_REFERENCE_V1','actuator_execution':False,'actual_dispensed_grams':None,'target_grams':35}
