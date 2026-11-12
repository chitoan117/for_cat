"""Optional GET-only routes to mount into the existing FastAPI app after review.
No app factory side effects, POST/device controls, producer identity headers or sockets.
"""
from fastapi import APIRouter, HTTPException, Request
from .ledger import POLICY


def mount(app, ledger, authorize):
    if not callable(authorize):
        raise ValueError('existing server-side access boundary required')
    router = APIRouter(prefix='/api/v1/closed-loop')

    def allowed(request):
        if authorize(request, 'VIEW_CAMERA') is not True:
            raise HTTPException(403, 'closed-loop read permission required')

    @router.get('/status')
    def status(request: Request):
        allowed(request)
        return dict(schema_version='forcat_closed_loop_view_v1', mass_policy=dict(POLICY),
                    execution_context='OFFLINE_SANDBOX', physical_validation='NOT_VERIFIED',
                    items=ledger.readonly(), actuator_execution=False)

    @router.get('/history')
    def history(request: Request):
        allowed(request)
        return dict(schema_version='forcat_closed_loop_view_v1', mass_policy=dict(POLICY),
                    execution_context='OFFLINE_SANDBOX', physical_validation='NOT_VERIFIED',
                    items=ledger.readonly('history'), actuator_execution=False)

    @router.get('/events')
    def events(request: Request):
        allowed(request)
        return ledger.readonly('events')

    app.include_router(router)
