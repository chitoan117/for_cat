"""Device-side prerequisites for a host CAT request; never drives an output."""
import math

def block_reason(status,now,received_at):
    if not math.isfinite(received_at) or not 0<=now-received_at<2.5:return 'DEVICE_STALE'
    if status.get('demo_exited') is not False:return 'PAUSED_OR_MODE_UNKNOWN'
    if status.get('inspect_required') is not False:return 'INSPECTION_REQUIRED_OR_UNKNOWN'
    if status.get('meal_phase') in ('CAPTURING','OBSERVING'):return 'MEAL_OBSERVATION'
    if status.get('bench_state') not in ('READY','MASS OK GATE?'):return 'DEVICE_BUSY_OR_FAULT'
    if status.get('dog_running') is True:return 'DOG_ALARM'
    grams=status.get('signed_g')
    if type(grams) not in (int,float) or not math.isfinite(grams):return 'SCALE_NOT_READY'
    if abs(grams)>2:return 'BOWL_NOT_EMPTY'
    return None
