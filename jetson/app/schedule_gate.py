"""Safe due-instance adapter; no autonomous scheduler/actuator is started tonight."""
import hashlib


class ScheduledRequestGate:
    def __init__(self, requests):
        self.requests = requests

    def submit_due(self, plan_id, scheduled_unix_ms, now_unix_ms, *, time_valid):
        if time_valid is not True:
            return {'candidate': False, 'reason': 'TIME_INVALID', 'actuator_execution': False}
        if not plan_id or len(plan_id) > 64 or not isinstance(scheduled_unix_ms, int) or scheduled_unix_ms <= 0:
            raise ValueError('invalid meal-plan due instance')
        if now_unix_ms < scheduled_unix_ms:
            return {'candidate': False, 'reason': 'NOT_DUE', 'actuator_execution': False}
        # A missed/old meal must be explicitly rescheduled, never burst-caught-up.
        if now_unix_ms - scheduled_unix_ms > 60000:
            return {'candidate': False, 'reason': 'MISSED_WINDOW_NO_CATCHUP', 'actuator_execution': False}
        instance = 'schedule_' + hashlib.sha256((plan_id + ':' + str(scheduled_unix_ms)).encode()).hexdigest()[:48]
        request = self.requests.enqueue(instance, 'SCHEDULED', '', 35)
        return {'candidate': True, 'reason': 'DUE_INSTANCE_DRY_RUN', 'request': request,
                'actuator_execution': False}
