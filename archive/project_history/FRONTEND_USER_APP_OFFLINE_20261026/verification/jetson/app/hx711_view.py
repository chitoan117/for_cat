"""Filtered gram display from verified host coefficients; controller stays unchanged."""
from collections import deque
from threading import RLock
import time

from app.hx711_calibration import CalibrationStore, CRITERIA, binding, number, raw_statistics, point_quality


class Hx711GramView:
    def __init__(self,path,clock=time.monotonic):
        self.store=CalibrationStore(path);self.clock=clock;self.lock=RLock()
        self.window=deque(maxlen=CRITERIA['live_window_samples']);self.last_key=None;self.last_device_ms=None;self.host_boot=None;self.model_id=None

    def apply(self,state,bridge):
        with self.lock:
            return self._apply(state,bridge)

    def _apply(self,state,bridge):
        weight=state['weight']
        weight.update(grams=None,calibrated=False,calibration_valid=False,stable=None,stability_state='NOT_CALIBRATED',
            calibration_authority='JETSON_SQLITE_PHYSICAL_REFERENCE_V1',
            controller_calibration_state='UNCHANGED_NOT_AUTHORIZED_FOR_ACTUATION',
            tare_offset_counts=None,grams_per_count=None,counts_per_gram=None,calibration_id=None,
            raw_window_samples=0,raw_window_span_seconds=None,spread_grams=None,stddev_grams=None,
            sampled_at=bridge.get('last_received_at'),age_seconds=None)
        model=None
        try:model=self.store.active()
        except Exception as error:
            weight.update(calibration_state='INVALID_CALIBRATION',calibration_error=type(error).__name__)
            self.window.clear();return
        weight['calibration_state']='NOT_CALIBRATED' if model is None else model['calibration_state']
        telemetry=bridge.get('telemetry') or {};hx=(telemetry.get('sensors') or {}).get('hx711') or {}
        stamp=bridge.get('last_rx_monotonic_ms',bridge.get('updated_monotonic_ms'))
        age=(self.clock()*1000-stamp)/1000 if number(stamp) else None
        weight['age_seconds']=age if age is not None and age>=0 else None
        ms=telemetry.get('monotonic_ms');raw=hx.get('raw_counts');host=bridge.get('host_boot_id')
        if bridge.get('telemetry_usable_now') is not True or hx.get('raw_available') is not True or not number(raw) or not -8388608<raw<8388607 or type(ms) is not int or age is None or age<0 or age>3:
            self.window.clear();weight['stability_state']='UNAVAILABLE';return
        current_model=model.get('calibration_id') if model else None
        if host!=self.host_boot or (self.last_device_ms is not None and (ms<self.last_device_ms or ms-self.last_device_ms>3000)) or current_model!=self.model_id:
            self.window.clear();self.last_key=None
        self.host_boot=host;self.last_device_ms=ms;self.model_id=current_model
        key=(host,ms)
        if key!=self.last_key:
            self.window.append({'raw':raw,'device_ms':ms});self.last_key=key
        weight['raw_window_samples']=len(self.window)
        if len(self.window)>1:
            weight['raw_window_span_seconds']=(self.window[-1]['device_ms']-self.window[0]['device_ms'])/1000
        if model is None:return
        try:
            if model['binding']!=binding(bridge):
                weight.update(calibration_state='DEVICE_BINDING_MISMATCH');return
        except ValueError:
            weight.update(calibration_state='DEVICE_BINDING_MISMATCH');return
        weight.update(calibration_valid=True,calibration_id=model['calibration_id'],tare_offset_counts=model['tare_offset_counts'],
            grams_per_count=model['grams_per_count'],counts_per_gram=model['counts_per_gram'])
        if len(self.window)<CRITERIA['live_window_samples'] or weight['raw_window_span_seconds']<CRITERIA['live_minimum_span_s']:
            weight['stability_state']='WARMING_UP';return
        try:stats=raw_statistics(list(self.window),model['criteria'])
        except ValueError:
            weight['stability_state']='UNSTABLE';weight['stable']=False;return
        factor=model['grams_per_count'];grams=(stats['mean_raw']-model['tare_offset_counts'])*factor
        quality=point_quality(stats,factor,model['criteria'])
        weight.update(calibrated=True,stable=quality['stable'],stability_state='STABLE' if quality['stable'] else 'UNSTABLE',
            filtered_raw_counts=stats['mean_raw'],spread_counts=stats['spread_counts'],stddev_counts=stats['stddev_counts'],
            spread_grams=quality['spread_g'],stddev_grams=quality['stddev_g'])
        maximum=model['range_grams'][1]+max(CRITERIA['absolute_error_g'],35*CRITERIA['relative_error_fraction'])
        if grams < -CRITERIA['zero_error_g'] or grams>maximum:
            weight.update(calibration_state='OUT_OF_VALIDATED_RANGE',grams=None,calibrated=False);return
        weight.update(grams=grams,health='HEALTHY' if quality['stable'] else 'UNSTABLE')
