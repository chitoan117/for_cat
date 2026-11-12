"""Read-only calibration visibility; placement/capture writes are operator CLI only."""
from fastapi import APIRouter, Request
from app.hx711_calibration import CalibrationStore

router=APIRouter(prefix='/api/hx711')


@router.get('/status')
def status(request:Request):
    state=request.app.state.system_state.snapshot()
    return {'data_source':state['data_source'],'hx711':{'raw':state['weight'].get('raw_counts'),**state['weight']},'safety':state['safety'],
            'target_grams':35,'actual_dispensed_grams':None,'actuator_execution':False}


@router.get('/calibration')
def calibration(request:Request):
    try:return CalibrationStore(request.app.state.store_path).status()
    except Exception as error:
        return {'active':None,'latest_session':None,'calibration_state':'UNKNOWN',
                'error':type(error).__name__,'actuator_execution':False,'actual_dispensed_grams':None}
