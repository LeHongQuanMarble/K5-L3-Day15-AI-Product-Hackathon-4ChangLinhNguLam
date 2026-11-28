(function () {
'use strict';
var id = location.pathname.split('/').pop();
var room = (new URLSearchParams(location.search).get('room') || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
var roomToken = room ? (localStorage.getItem('ailab_room_' + room) || '') : '';
if (room) { var backLink = document.getElementById('back'); backLink.href = '/room/' + room; backLink.textContent = 'Về phòng'; }
var frame = document.getElementById('stage'), title = document.getElementById('title'), status = document.getElementById('status'), camBtn = document.getElementById('cam');
var errBox = document.getElementById('play-error'), errText = document.getElementById('play-error-msg'), retryBtn = document.getElementById('retry');
var data = null, host = null, speech = null, autoTried = false;
var debugEnabled = new URLSearchParams(location.search).get('debug') === '1', debugPanel = null;
var debugState = { lastRuntimeEvent: null };
if (debugEnabled) {
  debugPanel = document.createElement('pre'); debugPanel.setAttribute('aria-label', 'Chẩn đoán runtime');
  debugPanel.style.cssText = 'position:fixed;z-index:9999;right:10px;bottom:10px;max-width:min(420px,calc(100vw - 20px));max-height:42vh;overflow:auto;margin:0;padding:10px 12px;border:1px solid #64748b;border-radius:8px;background:#07111eef;color:#e2e8f0;font:12px/1.45 ui-monospace,monospace;white-space:pre-wrap;pointer-events:none';
  document.body.appendChild(debugPanel);
}
function updateDebug(next) {
  if (!debugEnabled || !debugPanel) return;
  if (next) debugState = Object.assign({}, debugState, next);
  var pred = debugState.prediction;
  debugPanel.textContent = 'RUNTIME DEBUG (real signals)\n' +
    'Media: ' + (debugState.media || '—') + ' / ' + (debugState.mediaActive ? 'active' : 'inactive') + '\n' +
    'Model: ' + (debugState.modelStatus || 'not-loaded') + '\n' +
    'Inference: ' + (debugState.inferenceRunning ? 'running' : 'waiting') + ' / ' + (debugState.inferenceFps || 0) + ' FPS\n' +
    'Prediction: ' + (pred ? pred.label + ' (' + Number(pred.confidence).toFixed(3) + ')' : '—') + '\n' +
    'Mapped action: ' + (debugState.mappedAction || '—') + '\n' +
    'Last event: ' + JSON.stringify(debugState.lastEvent || debugState.lastRuntimeEvent || null) + '\n' +
    'Error: ' + (debugState.error || '—');
}
updateDebug();
import('/js/host-input.js').then(function (mod) { speech = mod.createSpeech(frame, say); }).catch(function () {});
function say(t) { status.textContent = t; }
function toFrame(m, transfer) { frame.contentWindow.postMessage(m, '*', transfer || []); }
// Nhắc giáo viên: lỗi camera/micro không chặn lối chơi — fallback chuột luôn bật.
function mouseHint() { return ' Bạn vẫn có thể chơi trọn vẹn bằng chuột ngay bên dưới.'; }
function init() {
  var m = { type: 'camera.init', mode: 'play', locale: 'vi', theme: 'dark', options: {}, source: 'camera' };
  if (data.manifest.inputs) { m.inputs = data.manifest.inputs.map(function (i) { return { key: i.key, label: i.label }; }); }
  if (data.questions && data.questions.length) m.questions = data.questions;
  if (data.content && data.content.length) m.content = data.content;
  toFrame(m);
}
window.addEventListener('message', function (e) {
  if (e.source !== frame.contentWindow || !e.data) return;
  if (e.data.type === 'ready') {
    init(); if (host) host.status();
    // Vào chơi là tự mở camera/micro (một lần); lỗi hay bị từ chối thì chơi bằng chuột, nút bên trên để thử lại.
    if (host && !autoTried && !host.isRunning()) { autoTried = true; host.start(); }
  }
  if (e.data.type === 'speech' && speech) speech.message(e.data);
  if (e.data.type === 'camera.want' || e.data.type === 'hands') {
    updateDebug({ lastRuntimeEvent: { type: e.data.type, on: !!e.data.on, source: 'player' } });
    if (host) host.message(e.data);
    else if (e.data.type === 'hands' && e.data.on === true) toFrame({ type: 'camera.hand', hands: [], available: false });
  }
  if (e.data.type === 'finish') {
    say('Kết thúc: ' + (e.data.correct != null ? e.data.correct + '/' + e.data.total : ''));
    if (room && Number.isInteger(e.data.correct) && Number.isInteger(e.data.total)) sendScore(e.data.correct, e.data.total);
  }
});

// Chế độ phòng: gửi điểm về phòng, rồi quay lại bảng xếp hạng của phòng.
function sendScore(correct, total) {
  fetch('/api/rooms/' + room + '/score', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-Room-Token': roomToken }, body: JSON.stringify({ correct: correct, total: total }) })
    .then(function (r) { if (!r.ok) throw new Error(); say('Đã gửi điểm ' + correct + '/' + total + ' vào phòng. Đang về bảng xếp hạng…'); setTimeout(function () { location.href = '/room/' + room; }, 2500); })
    .catch(function () { say('Kết thúc: ' + correct + '/' + total + ' — chưa gửi được điểm vào phòng (chủ phòng có thể đã kết thúc).'); });
}
// Camera / micro do trang cha mở (js/host-input.js), trình chơi chỉ nhận kết quả qua postMessage.
function makeHost(d) {
  var thing = d.model.kind === 'audio' ? 'micro' : 'camera';
  camBtn.textContent = 'Bật ' + thing;
  return import('/js/host-input.js').then(function (mod) {
    host = mod.createHostInput({ frame: frame, model: d.model, mapping: d.mapping, sure: d.sure, holdMs: d.holdMs, fallbackHint: mouseHint(),
      onSay: say, onDiagnostics: updateDebug,
      onRunning: function (r) { camBtn.disabled = r === null; camBtn.textContent = (r ? 'Tắt ' : 'Bật ') + thing; } });
  });
}
function stopHost(keep) { if (host) host.stop(keep); if (speech) speech.stop(); }
camBtn.addEventListener('click', function () { if (host) host.isRunning() ? host.stop() : host.start(); });
window.addEventListener('pagehide', function () { stopHost(true); });

// Lỗi tải / chưa chơi được: gập khung chơi, mở vùng lỗi (có nút Thử lại → loadApp chạy lại được).
function showFail(head, why) {
  title.textContent = head;
  if (errText) errText.textContent = why || 'Có lỗi không rõ nguyên nhân.';
  if (errBox) errBox.hidden = false;
  frame.hidden = true;
  say(head + (why ? ' — ' + why : ''));
}
function loadApp() {
  autoTried = false; stopHost(true); host = null; // an toàn khi thử lại giữa chừng: tắt camera cũ, không đổi trạng thái của iframe
  if (errBox) errBox.hidden = true;
  frame.hidden = false;
  title.textContent = 'Đang nạp trò chơi…';
  say('Đang nạp trò chơi…');
  fetch(room ? '/api/rooms/' + room + '/play' : '/api/apps/' + id + '/play', { credentials: 'same-origin', headers: room ? { 'X-Room-Token': roomToken } : {} }).then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.message || 'Không mở được.'); return d; }); }).then(function (d) {
    if (d.unavailable) { showFail('Chưa chơi được', d.reason); return; }
    data = d; title.textContent = d.app.name; document.title = d.app.name + ' — AI Lab';
    var ready = d.model ? makeHost(d).then(function () { camBtn.hidden = false; say('Đang tự bật ' + (d.model.kind === 'audio' ? 'micro' : 'camera') + '…'); }).catch(function () { say('Không nạp được bộ đọc camera/micro.' + mouseHint()); }) : Promise.resolve();
    return ready.then(function () { frame.srcdoc = d.srcdoc; });
  }).catch(function (e) { showFail('Không mở được', e.message); });
}
if (retryBtn) retryBtn.addEventListener('click', loadApp);
loadApp();
})();
