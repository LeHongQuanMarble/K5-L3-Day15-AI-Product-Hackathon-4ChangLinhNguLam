/* Chatbot v2 (I01): tiếp quản tab #/chat sau app.js. JS thuần, không thư viện. */
(function () {
'use strict';
var appRoot = document.getElementById('app');
if (!appRoot) return;

function h(tag, attrs) {
  var el = document.createElement(tag);
  for (var k in (attrs || {})) {
    var v = attrs[k];
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
    else if (k === 'value') el.value = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
  return el;
}
function add(el, c) {
  if (c == null || c === false) return;
  if (Array.isArray(c)) return c.forEach(function (x) { add(el, x); });
  el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
}
function api(method, url, body) {
  var opt = { method: method, headers: {}, credentials: 'same-origin' };
  if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  return fetch(url, opt).then(function (r) {
    return r.json().catch(function () { return {}; }).then(function (d) {
      if (!r.ok) {
        var e = new Error((d && (d.message || (d.failure && d.failure.message))) || 'Có lỗi, thử lại.');
        e.status = r.status; e.code = d && d.error; throw e;
      }
      return d;
    });
  });
}
function newId() {
  try { if (window.crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (e) { /* bỏ qua */ }
  var s = 'r', c = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-';
  for (var i = 0; i < 24; i++) s += c.charAt(Math.floor(Math.random() * c.length));
  return s;
}
function hashId() {
  var m = /^#\/chat(?:\/([A-Za-z0-9_-]+))?\/?$/.exec(location.hash);
  return m ? (m[1] || null) : undefined; /* undefined = không phải tab chat */
}
function setHash(id) {
  try { history.replaceState(null, '', '#/chat/' + id); } catch (e) { /* bỏ qua */ }
}
function errBox(msg) { return h('div', { class: 'err', role: 'alert' }, String(msg)); }
function list(items) { return h('ul', { style: 'margin:4px 0 8px;padding-left:20px' }, items.map(function (t) { return h('li', null, String(t)); })); }

var instCounter = 0;
function build(page) {
  var chatId = null, state = null, msgs = [], busy = false, notice = '', sess = 0, inst = ++instCounter;
  var loading = false, loadErr = false, reqSeq = 0, loadSeq = 0, applied = 0;
  var log = h('div', { class: 'msgs', 'aria-live': 'polite' });
  var side = h('div', { class: 'list' });
  var input = h('textarea', { style: 'min-height:80px', maxlength: 2000, 'aria-label': 'Mô tả game',
    placeholder: 'Ví dụ: Game ôn bảng cửu chương, học sinh giơ tay trái/phải để chọn đáp án A/B, ai đúng nhiều nhất thắng.' });
  var send = h('button', { class: 'ail-btn pri', type: 'button' }, 'Gửi');
  var root = h('div', { class: 'chat', 'data-chatbot-v2': '1' }, side,
    h('div', null, log,
      h('div', { class: 'row', style: 'margin-top:10px;align-items:flex-end' }, h('div', { class: 'grow' }, input), send),
      h('div', { class: 'meta' }, 'Ctrl+Enter để gửi')));
  page.replaceChildren(h('div', null, h('div', { class: 'bar' }, h('h2', { class: 'sp sr' }, 'Trợ lý game')), root));

  /* phiên hiển thị: đổi chat/tạo mới/rời tab/bị dựng lại thì phản hồi cũ bị bỏ */
  function isLive(s) { return s === sess && inst === instCounter && root.isConnected; }
  function locked() { return busy || loading || loadErr; }
  function verOk(st) { return !(st && state && typeof st.stateVersion === 'number' && typeof state.stateVersion === 'number' && st.stateVersion < state.stateVersion); }
  function statusChip(st) {
    var map = { awaiting_confirmation: ['warn', 'Chờ xác nhận'], confirmed: ['ok', 'Đã xác nhận'], cancelled: ['bad', 'Đã hủy'] };
    var m = map[st] || ['', String(st || '')];
    return h('span', { class: 'ail-chip ' + m[0] }, m[1]);
  }
  function handleErr(e) {
    if (e.status === 409 && e.code === 'stale_version') {
      notice = 'Đã có bản mới hơn, đang tải lại.';
      return loadChat(chatId, true, sess);
    }
    notice = e.message || 'Có lỗi, thử lại.';
  }
  function act(p, action) {
    if (locked() || !chatId) return;
    var s = sess, cid = chatId;
    busy = true; notice = ''; drawLog();
    api('POST', '/api/chats/' + cid + '/actions', { action: action, proposalId: p.proposalId, version: p.version, requestId: newId() })
      .then(function () { if (isLive(s)) return loadChat(cid, true, s); })
      .catch(function (e) { if (isLive(s)) return handleErr(e); })
      .then(function () { if (!isLive(s)) return; busy = false; drawLog(); input.focus(); });
  }
  function planCard(s) {
    var p = s.proposal, box = h('div', { class: 'cardin' });
    box.appendChild(h('div', { class: 'ail-row' }, h('strong', null, 'Phương án (phiên bản ' + p.version + ')'), statusChip(p.status)));
    if (p.reason) box.appendChild(h('p', { class: 'ail-desc', style: 'margin:4px 0 8px' }, String(p.reason)));
    if (p.assumptions && p.assumptions.length) box.appendChild(h('div', null, h('div', { style: 'font-weight:500' }, 'Giả định'), list(p.assumptions.map(function (a) { return typeof a === 'string' ? a : (a.text || a.label || JSON.stringify(a)); }))));
    if (p.changes && p.changes.length) box.appendChild(h('div', null, h('div', { style: 'font-weight:500' }, 'Thay đổi'), list(p.changes.map(function (c) { return typeof c === 'string' ? c : (c.label || c.message || JSON.stringify(c)); }))));
    var im = p.interactionModel || {};
    box.appendChild(h('div', { class: 'meta' }, 'Điều khiển: Chuột: luôn bật' + (im.kind ? ' · ' + im.kind : '')));
    var w = p.warnings || [];
    if (w.length) {
      box.appendChild(h('div', { style: 'font-weight:500;margin:6px 0 4px' }, 'Cảnh báo (' + w.length + ')'));
      w.forEach(function (x) {
        box.appendChild(h('div', { class: 'note', style: 'margin:4px 0' }, h('div', { style: 'font-weight:500' }, x.label || x.code || ''), x.reason ? h('div', null, String(x.reason)) : null, x.message ? h('div', null, String(x.message)) : null));
      });
    }
    if (p.status === 'awaiting_confirmation') {
      box.appendChild(h('div', { class: 'row', style: 'margin-top:8px' },
        h('button', { class: 'ail-btn sm pri', type: 'button', disabled: locked(), onclick: function () { act(p, 'confirm_plan'); } }, 'Xác nhận phương án (phiên bản ' + p.version + ')'),
        h('button', { class: 'ail-btn sm bad', type: 'button', disabled: locked(), onclick: function () { act(p, 'cancel_plan'); } }, 'Hủy phương án')));
    } else if (p.status === 'confirmed') box.appendChild(h('div', { class: 'note' }, 'Bước chuẩn bị game sẽ có ở đợt sau.'));
    else if (p.status === 'cancelled') box.appendChild(h('div', { class: 'note' }, 'Phương án đã hủy, nhắn điều muốn đổi.'));
    return box;
  }
  function oldCard(p) {
    var box = h('div', { class: 'cardin' });
    box.appendChild(h('div', { class: 'ail-row' }, h('strong', null, p.name || 'Đề xuất cũ')));
    function decide(a) {
      var s = sess;
      api('POST', '/api/chats/' + chatId + '/proposals/' + p.index + '/' + a).then(function (r) { if (!isLive(s)) return; p.status = r.status; drawLog(); })
        .catch(function (e) { if (isLive(s)) box.appendChild(errBox(e.message)); });
    }
    if (p.status === 'pending') {
      box.appendChild(h('div', { class: 'row', style: 'margin-top:8px' },
        h('button', { class: 'ail-btn sm pri', type: 'button', onclick: function () { decide('accept'); } }, 'Thêm vào Trình chơi'),
        h('button', { class: 'ail-btn sm bad', type: 'button', onclick: function () { decide('reject'); } }, 'Không dùng')));
    } else box.appendChild(h('span', { class: 'ail-chip ' + (p.status === 'accepted' ? 'ok' : 'bad') }, p.status === 'accepted' ? 'Đã thêm vào Trình chơi' : p.status === 'rejected' ? 'Đã bỏ, không lưu' : 'Đã quyết định'));
    return box;
  }
  function drawLog() {
    log.replaceChildren();
    if (loading) log.appendChild(h('div', { class: 'meta chatbot-loading', role: 'status' }, 'Đang tải cuộc trò chuyện…'));
    else if (!msgs.length && !chatId) log.appendChild(h('div', { class: 'meta' }, 'Mô tả game bạn muốn: học sinh chơi thế nào, nội dung gì. Trợ lý sẽ hỏi lại nếu thiếu thông tin rồi đề xuất phương án để bạn xác nhận.'));
    msgs.forEach(function (m) {
      var el = h('div', { class: 'm ' + m.role }, m.text || '');
      if (m.role === 'bot') {
        if (m.simulated) el.appendChild(h('div', { class: 'meta' }, 'Chế độ giả — không phải AI thật' + (m.model ? ' (' + m.model + ')' : '')));
        if (m.error) el.appendChild(h('div', { class: 'err' }, String(m.error)));
        if (m.proposal && m.proposal.index != null) el.appendChild(oldCard(m.proposal));
      }
      log.appendChild(el);
    });
    var s = state;
    if (s && s.status === 'clarifying' && s.questions && s.questions.length) {
      log.appendChild(h('div', { class: 'm bot' }, h('div', { style: 'font-weight:500' }, 'Cần làm rõ thêm'), list(s.questions.map(function (q) { return q.text || q; }))));
    }
    if (s && s.proposal && s.proposal.proposalId) log.appendChild(planCard(s));
    if (notice) log.appendChild(errBox(notice));
    if (loadErr) log.appendChild(h('button', { class: 'ail-btn sm chatbot-retry', type: 'button', onclick: function () { notice = ''; loadChat(chatId, true, sess); } }, 'Thử tải lại'));
    if (busy) log.appendChild(h('div', { class: 'm bot dots', 'aria-label': 'Đang xử lý' }, h('span'), h('span'), h('span')));
    send.disabled = input.disabled = locked();
    log.scrollTop = log.scrollHeight;
  }
  function drawSide() {
    return api('GET', '/api/chats').then(function (d) {
      var btns = (d.chats || []).map(function (c) {
        return h('button', { class: 'ail-btn sm', type: 'button', onclick: function () { setHash(c.id); openChat(c.id); } }, String(c.title || c.id));
      });
      side.replaceChildren.apply(side, [h('button', { class: 'ail-btn', type: 'button', onclick: newChat }, 'Cuộc trò chuyện mới')].concat(btns));
    }).catch(function (e) { side.replaceChildren(errBox(e.message)); });
  }
  function newChat() {
    sess++; busy = false; loading = false; loadErr = false; chatId = null; state = null; msgs = []; notice = '';
    try { history.replaceState(null, '', '#/chat'); } catch (e) { /* bỏ qua */ }
    drawLog(); input.focus();
  }
  function openChat(id) {
    sess++; busy = false; loadErr = false; notice = ''; msgs = []; state = null; chatId = id;
    applied = 0;
    return loadChat(id, true, sess);
  }
  function loadChat(id, keepNotice, s) {
    if (!keepNotice) notice = '';
    var seq = ++reqSeq; loadSeq = seq; loading = true; loadErr = false; drawLog();
    return api('GET', '/api/chats/' + id).then(function (d) {
      if (!isLive(s)) return;
      if (seq >= applied && verOk(d.state)) {
        applied = seq; chatId = d.id || id; msgs = d.messages || []; state = d.state || null;
      }
      if (seq === loadSeq) { loading = false; }
      drawLog();
    }).catch(function (e) {
      if (!isLive(s)) return;
      if (seq === loadSeq) { loading = false; loadErr = true; notice = e.message || 'Không tải được cuộc trò chuyện.'; }
      drawLog();
    });
  }
  function submit() {
    var t = input.value.trim();
    if (locked() || t.length < 3) return;
    busy = true; notice = ''; msgs.push({ role: 'user', text: t }); input.value = ''; drawLog();
    var body = { chatId: chatId, text: t, requestId: newId() };
    if (chatId && state && state.stateVersion != null) body.expectedVersion = state.stateVersion;
    var wasNew = !chatId, s = sess, seq = ++reqSeq;
    api('POST', '/api/chat', body).then(function (d) {
      if (!isLive(s)) { if (wasNew) drawSide(); return; }
      chatId = d.chatId;
      if (seq < applied || !verOk(d.reply)) return;
      applied = seq; state = d.reply || null;
      msgs.push({ role: 'bot', text: (d.reply && d.reply.text) || '', simulated: d.reply && d.reply.simulated, model: d.reply && d.reply.model, error: d.reply && d.reply.error });
      if (wasNew) setHash(chatId);
      drawSide();
    }).catch(function (e) {
      if (!isLive(s)) return;
      if (e.status === 409 && e.code === 'stale_version') { notice = 'Đã có bản mới hơn, đang tải lại.'; input.value = t; return loadChat(chatId, true, s); }
      msgs.push({ role: 'bot', text: '', error: e.message });
    }).then(function () { if (!isLive(s)) return; busy = false; drawLog(); input.focus(); });
  }
  send.addEventListener('click', submit);
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); } });
  drawLog(); drawSide();
  var id = hashId();
  if (id) openChat(id);
}

function takeover() {
  if (hashId() === undefined) return;
  var main = document.getElementById('main');
  if (!main) return;
  var old = main.querySelector('.chat:not([data-chatbot-v2])');
  if (!old) return;
  var page = main.querySelector('.ail-page') || (old.parentNode && old.parentNode.parentNode);
  if (!page) return;
  build(page);
}

new MutationObserver(takeover).observe(appRoot, { childList: true, subtree: true });
window.addEventListener('hashchange', takeover);
takeover();
})();
