"""Read-only inox-bowl mass-difference policy. No serial/NVS/actuator API.

Gross means the calibrated scale reading before a bowl-baseline subtraction.
It does not claim the bowl's absolute physical mass when calibration was bowl-zeroed.
"""
from dataclasses import dataclass
import math
import statistics

@dataclass(frozen=True)
class Context:
    session_id: str
    mount_id: str
    calibration_id: str
    boot_id: str
    tare_generation: int = 0
    calibration_current_mount: bool = False
    physical_validated: bool = False
    gross_origin: str = 'CALIBRATED_SCALE_ORIGIN'

@dataclass(frozen=True)
class GrossSample:
    gross: float | None
    at_ms: int
    context: Context
    valid: bool = True

class BowlMassTracker:
    def __init__(self,context):
        if not all(isinstance(v,str) and v for v in (context.session_id,context.mount_id,context.calibration_id,context.boot_id)):
            raise ValueError('explicit session/mount/calibration/boot identity required')
        if context.calibration_current_mount is not True:
            raise ValueError('CURRENT_MOUNT_CALIBRATION_REQUIRED')
        self.context=context;self.phase='AWAITING_EMPTY_BOWL';self.empty_bowl_gross=None
        self.gross_before_dispense=self.gross_after_dispense=self.meal_start_gross=self.meal_end_gross=None
        self.actual_dispensed=None;self.started=None;self.food_name=None;self.reason=None;self.captured_once=False;self.peak_delta=0
        self.meal_last_at=None;self.meal_minimum=None

    def invalidate(self,reason):
        self.reason=reason;self.phase='BLOCKED';self.empty_bowl_gross=None

    def _window(self,samples,now):
        try:
            if type(now) is not int or len(samples)<4:raise ValueError('STABLE_WINDOW_REQUIRED')
            if any(s.context!=self.context for s in samples):raise ValueError('MOUNT_CALIBRATION_BOOT_OR_TARE_CHANGED')
            if any(s.valid is not True or type(s.gross) not in (int,float) or not math.isfinite(s.gross) or abs(s.gross)>1000 for s in samples):raise ValueError('INVALID_OR_OVER_CAPACITY_GROSS')
            ticks=[s.at_ms for s in samples]
            if any(type(t) is not int for t in ticks) or any(b<=a or b-a>750 for a,b in zip(ticks,ticks[1:])) or now<ticks[-1] or now-ticks[-1]>1500:raise ValueError('STALE_OR_INVALID_TIMESTAMPS')
            if ticks[-1]-ticks[0]<600:raise ValueError('STABLE_WINDOW_TOO_SHORT')
            values=[s.gross for s in samples];half=max(1,len(values)//2)
            if max(values)-min(values)>.2 or statistics.pstdev(values)>.05 or abs(statistics.fmean(values[:half])-statistics.fmean(values[-half:]))>.1:raise ValueError('UNSTABLE_OR_CREEPING_GROSS')
            return statistics.fmean(values)
        except ValueError as error:
            self.invalidate(str(error));raise

    def confirm_empty_bowl(self,samples,now,*,owner_confirmed_empty=False):
        if self.captured_once or self.phase in ('DISPENSING','OBSERVING'):raise ValueError('NEW_SESSION_REQUIRED_NO_REBASE_DURING_MEAL')
        if not owner_confirmed_empty:raise ValueError('OWNER_EMPTY_BOWL_CONFIRMATION_REQUIRED')
        value=self._window(samples,now);self.empty_bowl_gross=value;self.captured_once=True;self.phase='READY'
        return self.snapshot(gross_measurement=value)

    def _baseline(self):
        if self.empty_bowl_gross is None or self.phase=='BLOCKED':raise ValueError('FRESH_EMPTY_BOWL_BASELINE_REQUIRED')

    def begin_dispense(self,samples,now):
        self._baseline()
        if self.phase!='READY':raise ValueError('DISPENSE_NOT_READY')
        value=self._window(samples,now)
        if abs(value-self.empty_bowl_gross)>.2:
            self.invalidate('BOWL_NOT_EMPTY_OR_BASELINE_SHIFT');raise ValueError(self.reason)
        self.gross_before_dispense=value;self.started=now;self.phase='DISPENSING';self.peak_delta=0
        return self.snapshot(gross_measurement=value)

    def update_dispense(self,samples,now):
        self._baseline()
        if self.phase!='DISPENSING':raise ValueError('NOT_DISPENSING')
        if now<self.started or now-self.started>=20000:
            self.invalidate('DISPENSE_TIMEOUT');raise ValueError(self.reason)
        value=self._window(samples,now);delta=value-self.gross_before_dispense
        if delta>35.7 or delta<-.2 or delta+.7<self.peak_delta:
            self.invalidate('OVERSHOOT_OR_BOWL_CONTACT_OR_WEIGHT_DROP');raise ValueError(self.reason)
        self.peak_delta=max(self.peak_delta,delta)
        return self.snapshot(gross_measurement=value,actual_dispensed=delta,close_required=delta>=35)

    def finish_dispense(self,samples,now):
        reading=self.update_dispense(samples,now)
        if reading['actual_dispensed']<34.3:
            self.invalidate('UNDER_TARGET');raise ValueError(self.reason)
        self.gross_after_dispense=reading['gross_measurement'];self.actual_dispensed=self.gross_after_dispense-self.gross_before_dispense
        self.phase='DISPENSED';return self.snapshot(gross_measurement=self.gross_after_dispense,actual_dispensed=self.actual_dispensed)

    def begin_meal(self,food,samples,now):
        self._baseline()
        if self.phase!='DISPENSED' or not food:raise ValueError('SUCCESSFUL_DISPENSE_AND_FOOD_REQUIRED')
        value=self._window(samples,now)
        if abs(value-self.gross_after_dispense)>.2:
            self.invalidate('BOWL_DISTURBED_BEFORE_MEAL');raise ValueError(self.reason)
        self.meal_start_gross=value;self.started=now;self.food_name=food;self.phase='OBSERVING'
        self.meal_last_at=now;self.meal_minimum=value
        return self.snapshot(gross_measurement=value,starting_food_mass=value-self.empty_bowl_gross)

    def observe_meal(self,sample,now):
        self._baseline()
        if self.phase!='OBSERVING':raise ValueError('NOT_OBSERVING')
        if sample.context!=self.context or sample.valid is not True or type(sample.gross) not in (int,float) or not math.isfinite(sample.gross) or abs(sample.gross)>1000:
            self.invalidate('INVALID_MEAL_SAMPLE_OR_CONTEXT_CHANGED');raise ValueError(self.reason)
        if type(sample.at_ms) is not int or now<sample.at_ms or now-sample.at_ms>1500 or sample.at_ms<=self.meal_last_at or sample.at_ms-self.meal_last_at>1500:
            self.invalidate('MEAL_DATA_STALE_OR_GAP');raise ValueError(self.reason)
        if sample.gross<self.empty_bowl_gross-.2 or sample.gross>self.meal_minimum+.5:
            self.invalidate('BOWL_MOVED_REFILL_OR_CONTACT');raise ValueError(self.reason)
        self.meal_last_at=sample.at_ms;self.meal_minimum=min(self.meal_minimum,sample.gross)
        return self.snapshot(gross_measurement=sample.gross,food_delta=sample.gross-self.empty_bowl_gross)

    def finish_meal(self,samples,now,*,measurement_source='REAL_SENSOR_PENDING_VALIDATION'):
        self._baseline()
        if self.phase!='OBSERVING':raise ValueError('NOT_OBSERVING')
        if now<self.started: self.invalidate('CLOCK_REGRESSION');raise ValueError(self.reason)
        if now-self.started<60000:raise ValueError('OBSERVATION_WINDOW_NOT_FINISHED')
        if self.meal_last_at is None or now-self.meal_last_at>1500:
            self.invalidate('MEAL_CONTINUITY_NOT_VERIFIED');raise ValueError(self.reason)
        value=self._window(samples,now);remaining=value-self.empty_bowl_gross;consumed=self.meal_start_gross-value
        start_food=self.meal_start_gross-self.empty_bowl_gross
        self.meal_end_gross=value;self.phase='COMPLETE'
        if remaining<0 or consumed<0 or consumed>start_food:
            return self.snapshot(gross_measurement=value,remaining_food_mass=remaining,consumed=None,classification='UNCERTAIN',reason='INVALID_CONSUMPTION_OR_BOWL_CONTACT',measurement_source=measurement_source)
        label='LIKE' if consumed>=18 else 'DISLIKE' if consumed<=5 else 'UNCERTAIN'
        return self.snapshot(gross_measurement=value,starting_food_mass=start_food,remaining_food_mass=remaining,consumed=consumed,
                             classification=label,measurement_source=measurement_source,
                             inference='WEIGHT_LOSS_ONLY_NOT_PROOF_OF_ANIMAL_EATING')

    def check_empty_return(self,samples,now):
        self._baseline()
        if self.phase in ('DISPENSING','OBSERVING'):raise ValueError('NO_EMPTY_REBASE_DURING_ACTIVE_PHASE')
        value=self._window(samples,now);delta=value-self.empty_bowl_gross
        if abs(delta)>.2:
            self.invalidate('EMPTY_RETURN_DRIFT_RESIDUE_OR_BOWL_MOVED');raise ValueError(self.reason)
        return self.snapshot(gross_measurement=value,food_delta=delta)

    def reference_delta(self,samples,now):
        self._baseline()
        if self.phase in ('DISPENSING','OBSERVING'):raise ValueError('REFERENCE_TEST_OUTSIDE_ACTIVE_MEAL_ONLY')
        value=self._window(samples,now)
        return self.snapshot(gross_measurement=value,food_delta=value-self.empty_bowl_gross)

    def snapshot(self,**values):
        return {'phase':self.phase,'session_id':self.context.session_id,'mount_id':self.context.mount_id,
                'calibration_id':self.context.calibration_id,'boot_id':self.context.boot_id,'gross_origin':self.context.gross_origin,
                'empty_bowl_gross':self.empty_bowl_gross,'gross_before_dispense':self.gross_before_dispense,
                'gross_after_dispense':self.gross_after_dispense,'meal_start_gross':self.meal_start_gross,'meal_end_gross':self.meal_end_gross,
                'target_actual_dispensed':35,'food_name':self.food_name,'actuation_authorized':False,
                'physical_validated':False,'reason':self.reason,**values}
