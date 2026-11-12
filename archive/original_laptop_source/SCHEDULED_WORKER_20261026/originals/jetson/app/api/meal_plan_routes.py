"""Same-backend persistent plans; explicit preview only, never actuator execution."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from app.dry_run_requests import DryRunRequests
from app.meal_plans import CreatePlan, UpdatePlan, Revision, MealPlans, PlanMissing, PlanConflict, preview_plan

router = APIRouter(prefix='/api/meal-plans')


def service(request):
    if request.app.state.meal_plans is None:
        request.app.state.meal_plans = MealPlans(request.app.state.store_path)
    return request.app.state.meal_plans


def translate(operation):
    try:
        return operation()
    except PlanMissing as error:
        raise HTTPException(404, str(error)) from error
    except PlanConflict as error:
        raise HTTPException(409, str(error)) from error
    except OverflowError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(503, 'invalid meal plan configuration') from error


@router.get('')
def list_plans(request: Request):
    with request.app.state.meal_plan_lock:
        return translate(lambda: service(request).list())


@router.post('', status_code=201)
def create_plan(body: CreatePlan, request: Request):
    with request.app.state.meal_plan_lock:
        return translate(lambda: service(request).create(body))


@router.put('/{plan_id}')
def update_plan(plan_id: str, body: UpdatePlan, request: Request):
    with request.app.state.meal_plan_lock:
        return translate(lambda: service(request).update(plan_id, body))


@router.delete('/{plan_id}')
def delete_plan(plan_id: str, body: Revision, request: Request):
    with request.app.state.meal_plan_lock:
        return translate(lambda: service(request).delete(plan_id, body.expected_revision))


@router.post('/{plan_id}/preview')
def preview(plan_id: str, body: Revision, request: Request):
    with request.app.state.meal_plan_lock:
        def operation():
            plan = service(request).get(plan_id)
            if plan['revision'] != body.expected_revision:
                raise PlanConflict('plan changed; reload before preview')
            if request.app.state.esp32_reader is None:
                raise HTTPException(503, 'C++ arbiter integration not configured')
            return preview_plan(plan, DryRunRequests(Path(request.app.state.store_path).resolve()),
                                request.app.state.system_state.snapshot(), datetime.now(timezone.utc))
        return translate(operation)
