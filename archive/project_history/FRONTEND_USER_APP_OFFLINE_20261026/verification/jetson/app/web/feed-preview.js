/* One diagnostic request client for both views. No serial/actuator interface. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ForCatFeedPreview = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const reasons = {
    WEIGHT_NOT_CALIBRATED: 'Cân chưa hiệu chuẩn gram',
    TELEMETRY_UNSAFE_OR_STALE: 'Telemetry chưa đủ an toàn hoặc đã cũ',
    DISPENSE_BUSY: 'Hệ thống đang bận', COOLDOWN: 'Đang trong thời gian chờ',
    DUPLICATE_REQUEST: 'Request trùng đã được nhận trước đó',
    QUALIFIED_DRY_RUN: 'Đủ điều kiện dự kiến, nhưng thực thi vẫn bị khóa'
  };
  function validPending(value, source) {
    return value && typeof value === 'object' && !Array.isArray(value) &&
      typeof value.request_id === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(value.request_id) &&
      value.sub_source === source && value.target_grams === 35;
  }
  class FeedPreviewController {
    constructor(options) {
      if (!['KIOSK', 'APP'].includes(options.subSource)) throw new Error('Invalid manual sub-source');
      this.subSource = options.subSource;
      this.fetch = options.fetchImpl;
      this.storage = options.storage;
      this.crypto = options.cryptoImpl;
      this.now = options.now || (() => performance.now());
      this.sleep = options.sleep || (ms => new Promise(resolve => setTimeout(resolve, ms)));
      this.setTimer = options.setTimer || ((fn, ms) => globalThis.setTimeout(fn, ms));
      this.clearTimer = options.clearTimer || (id => globalThis.clearTimeout(id));
      this.pollMs = options.pollMs === undefined ? 250 : options.pollMs;
      this.windowMs = options.windowMs === undefined ? 20000 : options.windowMs;
      this.timeoutMs = options.timeoutMs === undefined ? 5000 : options.timeoutMs;
      this.clickGuardMs = options.clickGuardMs === undefined ? 1000 : options.clickGuardMs;
      this.lastNewIntentAt = -Infinity;
      this.onUpdate = options.onUpdate || (() => {});
      this.key = 'for_cat_manual_preview_v1_' + this.subSource.toLowerCase();
      this.ready = false; this.busy = false; this.pending = null; this.receipt = null;
      this.storageError = false; this.status = 'IDLE';
      this.message = 'Chỉ thử request qua arbiter; không cấp thức ăn.';
      try {
        const saved = this.storage.getItem(this.key);
        if (saved !== null) {
          const value = JSON.parse(saved);
          if (!validPending(value, this.subSource)) throw new Error('Invalid saved request');
          this.pending = value; this.status = 'SAVED_REQUEST';
          this.message = 'Có request chưa xác nhận; giữ nguyên ID để tra cứu/thử lại.';
        }
      } catch (_) {
        this.storageError = true; this.status = 'LOCAL_STORAGE_ERROR';
        this.message = 'Không đọc được ID request đã lưu. Chưa gửi request mới.';
      }
      this.notify();
    }
    view() {
      return {busy: this.busy, disabled: this.busy || !this.ready || this.storageError ||
          (!this.pending && this.now() - this.lastNewIntentAt < this.clickGuardMs),
        status: this.status, message: this.message, pendingId: this.pending ? this.pending.request_id : null,
        receipt: this.receipt, subSource: this.subSource,
        label: this.busy ? 'Đang kiểm tra request…' : this.pending ? 'Thử lại cùng request — DRY RUN' : 'Feed Now — DRY RUN'};
    }
    notify() { this.onUpdate(this.view()); }
    setReady(ready) { this.ready = ready === true; this.notify(); }
    newRequest() {
      if (!this.crypto || typeof this.crypto.getRandomValues !== 'function') throw new Error('Thiếu secure random; chưa tạo request');
      const bytes = new Uint8Array(16); this.crypto.getRandomValues(bytes);
      const nonce = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
      return {request_id: 'manual_' + this.subSource.toLowerCase() + '_' + nonce,
        sub_source: this.subSource, target_grams: 35};
    }
    async json(url, options) {
      const controller = new AbortController();
      const timer = this.setTimer(() => controller.abort(), this.timeoutMs);
      try {
        const response = await this.fetch(url, {...options, signal: controller.signal, cache: 'no-store'});
        const body = await response.json();
        if (!response.ok) {
          const detail = body && typeof body.detail === 'string' ? body.detail.slice(0, 200) : 'HTTP ' + response.status;
          throw new Error(detail);
        }
        return body;
      } finally { this.clearTimer(timer); }
    }
    validate(body) {
      const request = body && body.request;
      if (!this.pending || !request || request.request_id !== this.pending.request_id ||
          request.source !== 'MANUAL' || request.sub_source !== this.subSource || request.target_grams !== 35 ||
          request.actuator_execution !== false || request.actual_dispensed_grams !== null) {
        throw new Error('Response không khớp request DRY RUN; giữ nguyên ID');
      }
      if (body.decision !== null) {
        const decision = body.decision;
        if (!decision || decision.request_id !== request.request_id || decision.source !== 'MANUAL' ||
            decision.sub_source !== this.subSource || decision.target_grams !== 35 ||
            decision.status !== 'DRY_RUN_BLOCKED' || decision.reason !== 'UNATTENDED_SAFE_MODE' ||
            decision.actuator_execution !== false || decision.actual_dispensed_grams !== null ||
            typeof decision.qualification_reason !== 'string') {
          throw new Error('Decision không đúng contract DRY RUN; không coi là đã cấp thức ăn');
        }
      }
      this.receipt = body;
      return body.decision !== null;
    }
    complete() {
      this.status = 'DRY_RUN_BLOCKED';
      const reason = this.receipt.decision.qualification_reason;
      this.message = 'Đã xét DRY RUN — thực thi bị khóa. ' + reason + ' · ' + (reasons[reason] || 'Xem decision chi tiết');
      try { this.storage.removeItem(this.key); }
      catch (_) { this.message += ' · Không dọn được ID cũ; lần tải lại sẽ tra cứu cùng ID.'; }
      this.pending = null;
    }
    async run(mode) {
      this.busy = true; this.status = mode === 'POST' ? 'SUBMITTING' : 'RESUMING';
      this.message = mode === 'POST' ? 'Đang gửi một request DRY RUN…' : 'Đang tra cứu request đã lưu; không tạo request mới…';
      this.notify();
      try {
        const id = this.pending.request_id;
        const url = '/api/feed/preview/' + encodeURIComponent(id);
        let body = mode === 'POST' ? await this.json('/api/feed/preview', {
          method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(this.pending)
        }) : await this.json(url, {method: 'GET'});
        const deadline = this.now() + this.windowMs;
        while (true) {
          if (this.validate(body)) { this.complete(); return this.receipt; }
          this.status = 'QUEUED'; this.message = 'Đã nhận request; đang chờ cùng C++ arbiter xét DRY RUN…'; this.notify();
          if (this.now() >= deadline) throw new Error('Chưa có decision trong thời gian chờ; giữ ID để tra cứu/thử lại');
          await this.sleep(this.pollMs);
          body = await this.json(url, {method: 'GET'});
        }
      } catch (error) {
        this.status = 'RETRY_SAME_ID';
        this.message = String(error.message || error).slice(0, 300) + ' · Chưa xác nhận kết quả; thử lại vẫn dùng cùng request ID.';
        return null;
      } finally { this.busy = false; this.notify(); }
    }
    async submit() {
      if (this.busy || !this.ready || this.storageError) return null;
      if (!this.pending && this.now() - this.lastNewIntentAt < this.clickGuardMs) return null;
      try {
        if (!this.pending) {
          this.pending = this.newRequest(); this.receipt = null; this.lastNewIntentAt = this.now();
          this.setTimer(() => this.notify(), this.clickGuardMs);
        }
        // Save BEFORE any network call so a lost response/reload cannot create
        // a second intent. POST retries use the same durable idempotent ID.
        this.storage.setItem(this.key, JSON.stringify(this.pending));
      } catch (error) {
        this.status = 'LOCAL_REQUEST_ERROR'; this.storageError = true;
        this.message = String(error.message || error).slice(0, 200) + ' · Request chưa được gửi.';
        this.notify(); return null;
      }
      return this.run('POST');
    }
    async resume() {
      if (!this.pending || this.busy || this.storageError) return null;
      return this.run('GET'); // reload recovery is READ ONLY; no automatic POST
    }
  }
  return {FeedPreviewController};
});
