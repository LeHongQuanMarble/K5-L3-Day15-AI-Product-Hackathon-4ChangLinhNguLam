/* Motion do AI soạn — luồng như learning (teachers/motions): trò chuyện với AI (cột trái) → kịch bản (cột giữa) → dựng bài và phiên bản (cột phải).
   Chat và yêu cầu đang mở được hỏi lại mỗi 3 giây (30 giây khi rảnh); yêu cầu xong thì nạp lại kịch bản và phiên bản.
   Trang danh sách: thẻ motion + ô tạo mới. Máy chủ: ailab/motions.py. */
import { h, api, ico, toast, errBox, confirmModal } from './dom.js';

var OPEN_MS = 1200, QUIET_MS = 30000;
var FAIL_TXT = {};
function when(t) { var d = new Date(t * 1000); return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }); }
function dur(s) { s = Math.round(s || 0); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }

/* ---------- danh sách ---------- */
export function motionsListView(ctx) {
  var input = h('input', { type: 'text', maxlength: '120', placeholder: 'Tên bài, ví dụ: Phân số lớp 4', 'aria-label': 'Tên motion mới' });
  var busy = false;
  function create(e) {
    e.preventDefault();
    if (busy) return; busy = true;
    api('POST', '/api/motions', { title: input.value }).then(function (d) { location.hash = '#/motions/' + d.motion.id; })
      .catch(function (er) { busy = false; toast(er.message, 'err'); });
  }
  var grid = h('div', { class: 'ail-mo-grid' });
  ctx.mount(h('div', { class: 'ail-create' },
    h('div', { class: 'ail-tb-top' }, h('div', null, h('h2', null, 'Motion'),
      h('p', { class: 'meta' }, 'Nói với AI bài bạn muốn dạy, AI viết kịch bản chia cảnh, bạn chỉnh rồi bấm Dựng bài để có video tương tác.')),
      h('a', { class: 'ail-btn', href: '#/create' }, 'Quay lại')),
    h('form', { class: 'ail-mo-new', onsubmit: create }, input, h('button', { type: 'submit', class: 'ail-btn pri' }, ico('wand'), 'Tạo motion')),
    grid));
  api('GET', '/api/motions').then(function (d) {
    if (!d.motions.length) { grid.replaceChildren(h('p', { class: 'meta' }, 'Chưa có motion nào. Đặt tên bài ở ô trên để bắt đầu.')); return; }
    grid.replaceChildren.apply(grid, d.motions.map(function (m) {
      var v = m.version;
      return h('a', { class: 'ail-kind-card ail-kind-pickcard ail-mo-card', href: '#/motions/' + m.id },
        h('strong', { class: 'ail-kind-title' }, m.title),
        h('span', { class: 'meta' }, v ? 'Bản ' + v.n + ' · ' + v.scenes + ' cảnh · ' + dur(v.seconds) : 'Chưa dựng bài'));
    }));
  }).catch(function (e) { grid.replaceChildren(errBox(e)); });
}

/* ---------- trang làm việc ---------- */
function chatItem(m, open, cancel) {
  var meta = m.meta || {}, at = h('span', { class: 'meta' }, when(m.at));
  function ev(tone, title, detail, extra) {
    return h('div', { class: 'ail-mo-ev is-' + tone, role: 'status' }, h('b', null, title), detail ? h('span', null, detail) : null, extra || null, at);
  }
  if (m.kind === 'text') return h('div', { class: 'ail-mo-msg ' + (m.role === 'teacher' ? 'me' : 'ai') }, h('div', null, m.body), at);
  if (m.kind === 'tool') {
    var st = meta.status || 'run', lab = { run: 'đang chạy…', ok: 'xong', bad: 'lỗi' }[st] || st;
    return h('details', { class: 'ail-mo-tool is-' + st, open: st === 'run' || st === 'bad' ? true : null },
      h('summary', null, h('code', null, meta.tool || 'công cụ'), h('span', null, ' · ' + lab + (meta.ms != null ? ' · ' + (meta.ms / 1000).toFixed(1) + ' giây' : ''))),
      h('dl', null, h('dt', null, 'Vào'), h('dd', null, meta.input || '—'), h('dt', null, 'Ra'), h('dd', null, meta.output || (st === 'run' ? '…' : '—'))));
  }
  switch (m.kind) {
    case 'build_queued':
      if (!(open && open.task === 'build' && open.id === m.requestId)) return ev('plain', 'Đã nhờ dựng bài');
      return ev('run', open.status === 'running' ? 'Đang dựng bài…' : 'Đang chờ tới lượt…',
        open.status === 'running' && open.total > 0 ? 'Cảnh ' + open.done + '/' + open.total : '',
        h('button', { type: 'button', class: 'ail-btn sm', onclick: cancel }, 'Huỷ'));
    case 'build_done': return ev('ok', 'Đã dựng xong bản ' + meta.version, (meta.scenes || 0) + ' cảnh · ' + dur(meta.seconds));
    case 'build_failed': case 'script_failed': return ev('bad', m.kind === 'build_failed' ? 'Không dựng được bài' : 'AI chưa viết được kịch bản', m.body);
    case 'script_changed': return ev('ok', 'Kịch bản đã thay đổi', m.body);
    case 'cancelled': return ev('plain', meta.task === 'build' ? 'Đã huỷ dựng bài' : 'Đã huỷ');
    default: return ev('plain', m.body || m.kind);
  }
}

export function motionView(ctx, parts) {
  var id = parseInt(parts[1], 10);
  var state = { motion: null, thread: { messages: [], open: null }, versions: [], sel: 0, dirty: false, sending: false };
  var timer = null, gone = false;

  var logEl = h('div', { class: 'ail-mo-log', role: 'log', 'aria-live': 'polite' });
  var msgIn = h('textarea', { rows: '2', maxlength: '4000', placeholder: 'Ví dụ: Viết bài về phân số cho lớp 4, 5 cảnh' , 'aria-label': 'Nhắn AI'});
  var sendBtn = h('button', { type: 'button', class: 'ail-btn pri', onclick: send }, ico('send'), 'Gửi');
  var scriptEl = h('textarea', { class: 'ail-mo-script', spellcheck: 'false', 'aria-label': 'Kịch bản', placeholder: '# Tiêu đề bài\n\n## Tên cảnh\nHình: 🎯\n- Ý chính\nLời: Câu thuyết minh' });
  var saveBtn = h('button', { type: 'button', class: 'ail-btn', onclick: saveScript }, 'Lưu kịch bản');
  var scriptNote = h('span', { class: 'meta' });
  var buildBtn = h('button', { type: 'button', class: 'ail-btn pri', onclick: build }, ico('play'), 'Dựng bài');
  var stage = h('div', { class: 'ail-mo-stage' });
  var verEl = h('div', { class: 'ail-mo-vers' });
  var titleEl = h('h2', null, '…');

  scriptEl.addEventListener('input', function () { state.dirty = true; scriptNote.textContent = 'Chưa lưu'; });
  msgIn.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

  function load(what) {
    var jobs = [];
    if (!what || what.motion) jobs.push(api('GET', '/api/motions/' + id).then(function (d) {
      state.motion = d.motion; titleEl.textContent = d.motion.title;
      if (!state.dirty) scriptEl.value = d.motion.script;
    }));
    if (!what || what.versions) jobs.push(api('GET', '/api/motions/' + id + '/versions').then(function (d) {
      var had = state.versions.length; state.versions = d.versions;
      if (!state.sel || d.versions.length !== had) state.sel = d.versions.length ? d.versions[0].n : 0;
      drawVersions();
    }));
    return Promise.all(jobs);
  }
  function poll() {
    if (gone || !logEl.isConnected) { clearTimeout(timer); return; }
    var wasOpen = state.thread.open && state.thread.open.id;
    api('GET', '/api/motions/' + id + '/messages').then(function (t) {
      state.thread = t; drawLog();
      var nowOpen = t.open && t.open.id;
      if (wasOpen && wasOpen !== nowOpen) load();
      timer = setTimeout(poll, t.open ? OPEN_MS : QUIET_MS);
    }).catch(function (e) { toast(e.message, 'err'); timer = setTimeout(poll, QUIET_MS); });
  }
  function kick() { clearTimeout(timer); poll(); }

  function drawLog() {
    var open = state.thread.open, atEnd = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 40;
    var items = state.thread.messages.map(function (m) { return chatItem(m, open, cancel); });
    if (!items.length) items = [h('p', { class: 'meta' }, 'Nói với AI bài bạn muốn dạy: môn, lớp, số cảnh. AI viết kịch bản ở cột giữa, bạn có thể nhắn tiếp để sửa.')];
    logEl.replaceChildren.apply(logEl, items);
    if (atEnd) logEl.scrollTop = logEl.scrollHeight;
    var busy = !!open || state.sending;
    sendBtn.disabled = busy; buildBtn.disabled = busy;
    msgIn.placeholder = open && open.task === 'script' ? 'AI đang viết…' : msgIn.placeholder;
  }
  function drawVersions() {
    verEl.replaceChildren.apply(verEl, state.versions.map(function (v) {
      return h('button', { type: 'button', class: 'ail-btn sm' + (v.n === state.sel ? ' pri' : ''), 'aria-pressed': v.n === state.sel ? 'true' : 'false',
        onclick: function () { state.sel = v.n; drawVersions(); } }, 'Bản ' + v.n + ' · ' + dur(v.seconds));
    }));
    if (!state.versions.length) { stage.replaceChildren(h('p', { class: 'meta ail-mo-empty' }, 'Chưa có bản nào. Viết kịch bản rồi bấm “Dựng bài”.')); return; }
    var cur = stage.firstChild;
    var src = '/api/motions/' + id + '/versions/' + state.sel + '/play';
    if (cur && cur.tagName === 'IFRAME' && cur.getAttribute('data-src') === src) return;
    var f = h('iframe', { class: 'ail-mo-frame', title: 'Xem motion bản ' + state.sel, sandbox: 'allow-scripts', allow: 'autoplay; fullscreen', allowfullscreen: true, 'data-src': src });
    f.src = src; stage.replaceChildren(f);
  }

  function send() {
    var body = msgIn.value.trim(); if (!body || state.sending) return;
    state.sending = true; drawLog();
    api('POST', '/api/motions/' + id + '/messages', { body: body }).then(function () { msgIn.value = ''; })
      .catch(function (e) { toast(e.message, 'err'); })
      .then(function () { state.sending = false; kick(); });
  }
  function saveScript() {
    saveBtn.disabled = true;
    api('PUT', '/api/motions/' + id + '/script', { script: scriptEl.value }).then(function () {
      state.dirty = false; scriptNote.textContent = 'Đã lưu'; kick();
    }).catch(function (e) { toast(e.message, 'err'); }).then(function () { saveBtn.disabled = false; });
  }
  function build() {
    var go = function () {
      api('POST', '/api/motions/' + id + '/build').then(kick).catch(function (e) { toast(e.message, 'err'); });
    };
    if (state.dirty) { saveBtn.disabled = true; api('PUT', '/api/motions/' + id + '/script', { script: scriptEl.value }).then(function () { state.dirty = false; scriptNote.textContent = 'Đã lưu'; go(); }).catch(function (e) { toast(e.message, 'err'); }).then(function () { saveBtn.disabled = false; }); }
    else go();
  }
  function cancel() {
    var o = state.thread.open; if (!o) return;
    api('POST', '/api/motions/' + id + '/requests/' + o.id + '/cancel').catch(function () {}).then(kick);
  }
  function remove() {
    confirmModal('Xoá motion', 'Xoá motion này cùng kịch bản và mọi bản đã dựng?', 'Xoá', true).then(function (ok) {
      if (!ok) return;
      api('DELETE', '/api/motions/' + id).then(function () { location.hash = '#/motions'; }).catch(function (e) { toast(e.message, 'err'); });
    });
  }

  ctx.mount(h('div', { class: 'ail-mo' },
    h('div', { class: 'ail-tb-top' }, titleEl, h('div', { style: 'display:flex;gap:8px' },
      h('a', { class: 'ail-btn', href: '#/motions' }, 'Danh sách'), h('button', { type: 'button', class: 'ail-btn bad', onclick: remove }, 'Xoá'))),
    h('div', { class: 'ail-mo-cols' },
      h('section', { class: 'ail-mo-col', 'aria-label': 'Trò chuyện với AI' }, h('h3', null, '1 · Trò chuyện'), logEl, h('div', { class: 'ail-mo-compose' }, msgIn, sendBtn)),
      h('section', { class: 'ail-mo-col', 'aria-label': 'Kịch bản' }, h('h3', null, '2 · Kịch bản'), scriptEl, h('div', { class: 'ail-mo-row' }, saveBtn, scriptNote)),
      h('section', { class: 'ail-mo-col', 'aria-label': 'Kết quả' }, h('h3', null, '3 · Kết quả'), stage, verEl, h('div', { class: 'ail-mo-row' }, buildBtn)))));
  load().then(function () { poll(); }).catch(function (e) { ctx.mount(errBox(e)); });
  window.addEventListener('hashchange', function stop() { gone = true; clearTimeout(timer); window.removeEventListener('hashchange', stop); });
}
