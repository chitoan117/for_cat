"""Closed-loop V1 payload contract; ASCII manual diagnostic is never accepted."""
import math
import struct
from .wire import Command, Frame, ProtocolError

HEADER = struct.Struct('<BIII')
CONFIG = struct.Struct('<4H3HB5f')
RESULT = struct.Struct('<BIIII4BH3f')
CAP = struct.Struct('<BIIIBI3BH')
COMPLETE_FLAGS = 127


def header(boot, session, sequence):
    if any(type(x) is not int or not 0 < x <= 0xffffffff for x in (boot, session, sequence)):
        raise ProtocolError('nonzero boot/session/sequence required')
    return HEADER.pack(1, boot, session, sequence)


def configuration(values):
    if len(values) != 13:
        raise ProtocolError('13 reviewed settings required')
    return CONFIG.pack(*values)


def capabilities(frame):
    if frame.command != Command.CAPABILITIES or len(frame.payload) != CAP.size:
        raise ProtocolError('explicit closed-loop capabilities required')
    schema, boot, session, seq, flags, last, pending, state, reason, calibration = CAP.unpack(frame.payload)
    if schema != 1 or not boot or not session or flags & ~15 or last > 0xffffff or pending not in (0, 1):
        raise ProtocolError('capabilities schema/identity')
    return dict(boot=boot, session=session, sequence=seq, enabled=bool(flags & 1), ready=bool(flags & 2),
                closure_available=bool(flags & 4), configured=bool(flags & 8), last_id=last,
                inspection_required=bool(pending), state=state, reason=reason, calibration_id=calibration)


def result(frame):
    if frame.command != Command.RESULT or len(frame.payload) != RESULT.size:
        raise ProtocolError('request-bound final payload required')
    schema, boot, session, seq, origin, code, state, reason, flags, calibration, target, actual, latest = RESULT.unpack(frame.payload)
    if schema != 1 or not boot or not origin or not 0 < frame.request_id <= 0xffffff or target != 35 or flags & ~127 or code not in (0, 1, 3) or state not in range(10):
        raise ProtocolError('result schema/target/identity')
    final = bool(flags & 1)
    if final != (code != 0) or (code == 1 and (flags != COMPLETE_FLAGS or state != 8 or reason != 0 or not calibration or not math.isfinite(actual) or not 30 <= actual <= 40)):
        raise ProtocolError('mass/closure/settle/PWM/journal/calibration final mismatch')
    if flags & 32 and (not math.isfinite(actual) or not -1000 <= actual <= 1000):
        raise ProtocolError('invalid measurement')
    return dict(request_id=frame.request_id, boot=boot, session=session, sequence=seq, origin_session=origin,
                state='COMPLETE' if code == 1 else 'FAULT' if final else 'PENDING', reason=reason,
                controller_state=state,
                servo_command_state=('DISARMED','ARMED_CLOSE_COMMAND','WAIT_BASELINE_CLOSE_COMMAND','OPEN_COMMAND',
                    'CLOSE_COMMAND','WAIT_SETTLE_PWM_OFF','MEASURE_PWM_OFF','FAULT_CLOSING_COMMAND','TERMINAL_PWM_OFF','FAULT_COMMAND')[state],
                final_status_received=final, flags=flags, calibration_id=calibration, target_grams=35,
                actual_dispensed_grams=float(actual) if flags & 32 else None,
                latest_observed_grams=float(latest) if math.isfinite(latest) else None,
                closed=bool(flags & 8), settled=bool(flags & 2), pwm_off=bool(flags & 4),
                journal_committed=bool(flags & 16), calibration_valid=bool(flags & 64))
