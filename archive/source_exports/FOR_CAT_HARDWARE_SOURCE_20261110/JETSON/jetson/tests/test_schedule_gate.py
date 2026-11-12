from app.dry_run_requests import DryRunRequests
from app.schedule_gate import ScheduledRequestGate


def test_invalid_jetson_time_blocks_due_instance(tmp_path):
    gate = ScheduledRequestGate(DryRunRequests(tmp_path / 'scheduled.db'))
    assert gate.submit_due('meal', 1000, 2000, time_valid=False)['reason'] == 'TIME_INVALID'
    assert not (tmp_path / 'scheduled.db').exists()


def test_valid_due_instance_uses_shared_arbiter_inbox_and_35g(tmp_path):
    gate = ScheduledRequestGate(DryRunRequests(tmp_path / 'scheduled.db'))
    first = gate.submit_due('meal', 1000, 2000, time_valid=True)
    assert first['candidate'] is True and first['actuator_execution'] is False
    assert first['request']['request']['source'] == 'SCHEDULED'
    assert first['request']['request']['target_grams'] == 35
    assert first['request']['request']['actual_dispensed_grams'] is None
    assert gate.submit_due('meal', 1000, 2500, time_valid=True)['request'] == first['request']


def test_future_and_missed_meals_do_not_make_requests(tmp_path):
    gate = ScheduledRequestGate(DryRunRequests(tmp_path / 'unused.db'))
    assert gate.submit_due('meal', 5000, 1000, time_valid=True)['reason'] == 'NOT_DUE'
    assert gate.submit_due('meal', 1000, 70000, time_valid=True)['reason'] == 'MISSED_WINDOW_NO_CATCHUP'
