"""CAT-at-reviewed-FOOD_ROI transaction gate, no model/camera/serial code.
Uses existing framed producer validation; generic CAT remains class-only, not identity.
"""
from .ai_contract import validate
from .wire import Command
import hashlib


class AutoGate:
    def __init__(self, client, ledger, host_boot, roi_review_id):
        self.client, self.ledger, self.host_boot = client, ledger, host_boot
        self.review_id = roi_review_id
        self.key = 'auto_gate:' + roi_review_id
        self.state = ledger.meta(self.key) or dict(host_boot=host_boot, latched=False, visits=0, last_feed=None, last_dog=None)
        self.epoch = None; self.retired = set(); self.sequence = 0; self.captured = 0
        self.confirmations = 0; self.first_cat = None; self.absent_since = None; self.last_now = 0

    def _save(self):
        self.ledger.set_meta(self.key, self.state)

    def _abort(self, now):
        if self.client.active_id is not None and self.client.cap:
            try:
                self.client.command(Command.ABORT, now, request_id=self.client.active_id)
            except Exception:
                self.client.disconnect('AI_INVALID_ABORT_UNCONFIRMED')

    def observe(self, data, now, safety):
        if now < self.last_now or self.state['host_boot'] != self.host_boot:
            if self.client.active_id is not None:
                self.client.disconnect('CLOCK_OR_HOST_BOOT_CHANGE_REVIEW')
            return 'BLOCKED_RESTART_OR_CLOCK_REVIEW'
        self.last_now = now
        try:
            frame = validate(data, now, self.host_boot)
        except (ValueError, TypeError, KeyError):
            self._abort(now)
            self.confirmations = 0; self.first_cat = None
            return 'BLOCKED_AI_METADATA_OR_STALE'
        epoch = frame['producer_epoch']
        if epoch in self.retired:
            return 'BLOCKED_RETIRED_AI_EPOCH'
        if epoch != self.epoch:
            if self.epoch is not None:
                self.retired.add(self.epoch)
            if len(self.retired) > 32:
                return 'BLOCKED_AI_EPOCH_BUDGET'
            self.epoch = epoch; self.sequence = self.captured = 0; self.confirmations = 0; self.first_cat = None
        if frame.get('health') != 'ONLINE':
            self._abort(now)
            self.confirmations = 0; self.first_cat = None
            return 'BLOCKED_AI_DISCONNECTED'
        if frame['roi_sequence'] <= self.sequence or frame['roi_observation_ms'] < self.captured:
            return 'NO_NEW_AI_EVIDENCE'
        self.sequence, self.captured = frame['roi_sequence'], frame['roi_observation_ms']
        dog = frame['classification'] == 'DOG' or any(x['species'] == 'DOG' for x in frame['detections'])
        if dog:
            self.confirmations = 0; self.first_cat = None; self.absent_since = None
            last = self.state['last_dog']
            if last is None or now-last >= 60000:
                self.state['last_dog'] = now; self._save()
                self.client.dog(now)
                return 'DOG_ABORT_AND_BOUNDED_WARNING_REQUEST_NO_FEED'
            self._abort(now)
            return 'DOG_NO_FEED_COOLDOWN'
        if frame['classification'] == 'NONE':
            self._abort(now)
            self.confirmations = 0; self.first_cat = None
            if self.absent_since is None:
                self.absent_since = now
            if now-self.absent_since >= 2000:
                self.state['latched'] = False; self._save()
            return 'NONE_NO_OUTPUT'
        self.absent_since = None
        if not self.review_id or frame['roi_mode'] != 'ROI_ENABLED' or frame.get('roi_calibrated') is not True or not frame['roi_decision_eligible']:
            self._abort(now)
            self.confirmations = 0; self.first_cat = None
            return 'BLOCKED_FOOD_ROI'
        if frame['classification'] != 'CAT' or frame['confidence'] < .9:
            self._abort(now)
            self.confirmations = 0; self.first_cat = None
            return 'NO_QUALIFIED_CAT'
        if self.state['latched']:
            return 'VISIT_ALREADY_CONSUMED'
        if self.first_cat is None:
            self.first_cat = now
        self.confirmations += 1
        if self.confirmations < 3 or now-self.first_cat < 500:
            return 'CONFIRMING_CAT'
        last = self.state['last_feed']
        if last is not None and now-last < 7200000:
            return 'FEED_COOLDOWN'
        required = ('weight_healthy', 'weight_fresh', 'calibration_valid', 'servo_reviewed', 'power_reviewed', 'journal_ready')
        if any(safety.get(k) is not True for k in required):
            return 'BLOCKED_SENSOR_OR_PHYSICAL_GATES'
        cap = self.client.cap
        if not self.client.authority or not cap or not cap['enabled'] or not cap['closure_available'] or not cap['ready'] or not cap['configured'] or safety.get('calibration_id') != cap['calibration_id']:
            return 'BLOCKED_CLOSED_LOOP_FIRMWARE_CAPABILITY'
        # Consume visit durably BEFORE reserving/transmitting, even if transport fails.
        self.state['latched'] = True; self.state['visits'] += 1; self.state['last_feed'] = now; self._save()
        identity = hashlib.sha256((self.host_boot+'\0'+self.review_id).encode()).hexdigest()
        key = 'CAT:' + identity + ':' + str(self.state['visits'])
        return self.client.request(key, now)
