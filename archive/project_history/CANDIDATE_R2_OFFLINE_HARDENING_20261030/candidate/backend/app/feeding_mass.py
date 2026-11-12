"""Owner policy: control aim35, final band30..40. Never infer grams from ACK."""
from math import isfinite
POLICY={'target_grams':35.0,'tolerance_grams':5.0,'minimum_accepted_grams':30.0,'maximum_accepted_grams':40.0,'inclusive_bounds':True,'control_cutoff_grams':35.0}
def in_band(value):
    return type(value) in (int,float) and isfinite(value) and 30.0<=value<=40.0
def details(actual=None,observed=None,source='UNAVAILABLE_ON_WIRE',final_received=False):
    for v in (actual,observed):
        if v is not None and (type(v) not in (int,float) or not isfinite(v) or v<0):raise ValueError('invalid measured mass')
    return {'mass_policy':dict(POLICY),'actual_dispensed_grams':actual,'latest_observed_grams':observed,
        'mass_in_band':in_band(actual) if actual is not None else None,
        'observed_mass_in_band':in_band(observed) if observed is not None else None,
        'error_from_target_grams':actual-35 if actual is not None else None,
        'measurement_source':source,'final_status_received':final_received}
