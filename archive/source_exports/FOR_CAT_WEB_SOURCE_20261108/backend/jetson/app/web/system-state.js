'use strict';
const el = id => document.getElementById(id);
const put = (id, value) => { el(id).textContent = value === null || value === undefined ? '—' : String(value); };
const flag = value => value === true ? 'true' : value === false ? 'false' : 'UNKNOWN';
const distance = sensor => sensor && sensor.valid && Number.isFinite(sensor.distance_cm) ? sensor.distance_cm.toFixed(2) + ' cm' : '—';
let lastMessage = 0;
let backoff = 500;
el('view-name').textContent = location.pathname === '/app' ? 'App' : 'Kiosk';
let feedPreview = null;
if (window.ForCatFeedPreview && el('feed-preview')) {
  try {
    feedPreview = new window.ForCatFeedPreview.FeedPreviewController({
      subSource: location.pathname === '/app' ? 'APP' : 'KIOSK',
      fetchImpl: window.fetch.bind(window), storage: window.localStorage, cryptoImpl: window.crypto,
      onUpdate: view => {
        el('feed-preview').disabled = view.disabled; put('feed-preview', view.label);
        put('feed-request-status', view.message);
        put('feed-request-id', 'Request ID: ' + (view.pendingId || (view.receipt && view.receipt.request.request_id) || '—'));
        put('feed-request-result', view.receipt ? JSON.stringify(view.receipt, null, 2) : 'null');
      }
    });
    el('feed-preview').addEventListener('click', () => feedPreview.submit());
    feedPreview.resume();
  } catch (_) { put('feed-request-status', 'Không khởi tạo được request client; chưa gửi request.'); }
}

function unavailable(reason) {
  if (feedPreview) feedPreview.setReady(false);
  put('connection', reason); el('connection').dataset.live = 'false';
  for (const id of ['esp32','ai','motion','approach','water','weight','oled','button','safety','time','behavior']) put(id, 'UNKNOWN');
  for (const id of ['esp32-detail','ai-detail','motion-detail','approach-detail','water-detail','weight-detail','button-detail','safety-detail']) put(id, 'Realtime unavailable — readings hidden');
  put('updated', 'Mất cập nhật backend; không hiển thị số cũ như dữ liệu live.');
  put('raw-state', 'null');
}

function render(state) {
  lastMessage = Date.now();
  if (feedPreview) feedPreview.setReady(state.data_source === 'REAL' && state.esp32.connected === true &&
    state.feed.target_grams === 35 && state.feed.actuator_execution === false &&
    state.safety.servo_armed === false && state.safety.pump_armed === false &&
    state.safety.auto_feed === false && state.safety.auto_water === false &&
    state.safety.actuator_outputs_enabled === 0 && state.safety.actuator_execution === false);
  put('connection', state.data_source + ' · backend live · ' + state.esp32.health);
  el('connection').dataset.live = String(state.esp32.connected);
  put('esp32', state.esp32.health);
  put('esp32-detail', (state.esp32.device || 'Chưa có tty') + ' · RX: ' + (state.esp32.last_telemetry_at || 'null'));
  put('ai', state.ai.classification); put('ai-detail', state.ai.health + ' · ' + (state.ai.last_observation_at || 'null'));
  put('motion', state.pir.motion === null ? 'UNKNOWN' : state.pir.motion ? 'MOTION' : 'NO MOTION');
  put('motion-detail', state.pir.health + ' · transitions=' + (state.pir.transition_count ?? 'null'));
  put('approach', distance(state.approach)); put('approach-detail', state.approach.health + ' · valid=' + state.approach.valid);
  put('water', distance(state.water_operational)); put('water-detail', state.water_operational.health + ' · valid=' + state.water_operational.valid);
  put('weight', state.weight.calibrated && state.weight.grams !== null ? state.weight.grams + ' g' : 'grams: null');
  put('weight-detail', state.weight.health + ' · raw=' + (state.weight.raw_counts ?? 'null') + ' · calibrated=' + state.weight.calibrated);
  put('oled', state.oled.health);
  put('button', state.manual_button.pressed === null ? 'UNKNOWN' : state.manual_button.pressed ? 'PRESSED · LOW' : 'RELEASED · HIGH');
  put('button-detail', state.manual_button.health + ' · requests=' + (state.manual_button.request_count ?? 'null') + ' · raw=' + (state.manual_button.raw_level ?? 'null') + ' · stable=' + (state.manual_button.debounced_level ?? 'null') + ' · source=' + (state.manual_button.state_source || 'UNKNOWN'));
  put('safety', 'servo=' + flag(state.safety.servo_armed) + ' · pump=' + flag(state.safety.pump_armed));
  put('safety-detail', state.safety.servo_state + ' / ' + state.safety.pump_state + ' · auto_feed=' + flag(state.safety.auto_feed) + ' · auto_water=' + flag(state.safety.auto_water) + ' · outputs=' + (state.safety.actuator_outputs_enabled ?? 'UNKNOWN'));
  put('time', state.time.time_valid ? 'TIME_VALID' : 'TIME_INVALID');
  put('behavior', state.decisions.food_behavior);
  put('decision-detail', (state.decisions.near_configured ? 'Near stable=' + state.decisions.near_stable : 'NEAR_THRESHOLD_NOT_CONFIGURED') + ' · water=' + state.decisions.water_reason + ' · execution=false');
  put('updated', 'SystemState: ' + state.observed_at + ' · mode=' + state.data_source);
  put('raw-state', JSON.stringify(state, null, 2));
}

async function initial() {
  try { const response = await fetch('/api/status', {cache:'no-store'}); if (!response.ok) throw new Error('status'); render(await response.json()); }
  catch (_) { unavailable('Không đọc được REST state'); }
}
function connect() {
  const socket = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/ws/state');
  socket.onmessage = event => { try { render(JSON.parse(event.data)); backoff = 500; } catch (_) { unavailable('Invalid state'); } };
  socket.onclose = () => { unavailable('Realtime disconnected'); setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 10000); };
  socket.onerror = () => socket.close();
}
setInterval(() => { if (lastMessage && Date.now() - lastMessage > 4000) unavailable('Realtime STALE'); }, 1000);
initial(); connect();
