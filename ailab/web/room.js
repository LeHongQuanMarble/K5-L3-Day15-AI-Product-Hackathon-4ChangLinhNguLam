(function () {
'use strict';
var root = document.getElementById('root');
var m = location.pathname.match(/^\/room\/([A-Za-z0-9]+)/);
var code = m ? m[1].toUpperCase() : '';
var KEY = 'ailab_room_' + code;
var timer = 0, busy = false, last = null, redirected = false, nameDraft = '';

function h(tag, attrs) {
  var el = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) {
    if (k === 'class') el.className = attrs[k];
    else if (k.indexOf('on') === 0) el.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] != null) el.setAttribute(k, attrs[k]);
  });
  for (var i = 2; i < arguments.length; i++) { var c = arguments[i]; if (c != null) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); }
  return el;
}
function api(method, path, body) {
  var tk = localStorage.getItem(KEY);
  return fetch('/api/rooms' + path, { method: method, credentials: 'same-origin', headers: Object.assign({ 'X-Room-Token': tk || '' }, body ? { 'Content-Type': 'application/json' } : {}), body: body ? JSON.stringify(body) : undefined })
    .then(function (r) { return r.json().then(function (d) { if (!r.ok) { var e = new Error(d.message || 'Có lỗi.'); e.code = d.error; throw e; } return d; }); });
}
function msg(text, bad) { var p = root.querySelector('.msg'); if (p) { p.textContent = text || ''; p.className = 'msg muted' + (bad ? ' err' : ''); } }

// ---- chưa có mã: ô nhập mã ----
function joinByCode() {
  var inp = h('input', { placeholder: 'Mã phòng (6 ký tự)', maxlength: '6', 'aria-label': 'Mã phòng', autocomplete: 'off' });
  function go() { var v = inp.value.trim().toUpperCase(); if (v) location.href = '/room/' + v; }
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
  root.replaceChildren(h('h1', null, 'Vào phòng chơi'), h('div', { class: 'card' }, h('p', { class: 'muted' }, 'Nhập mã phòng do giáo viên (chủ phòng) cung cấp.'),
    h('div', { class: 'row' }, inp, h('button', { class: 'ail-btn pri', onclick: go }, 'Vào')), h('p', { class: 'msg muted' })));
  inp.focus();
}

function memberList(s, hostMode) {
  var ul = h('ol', null);
  if (!s.members.length) ul.appendChild(h('li', null, h('span', { class: 'muted' }, 'Chưa có ai vào phòng.')));
  s.members.forEach(function (x) {
    var done = x.finished != null;
    var li = h('li', { class: s.me && s.me.id === x.id ? 'me' : '' },
      h('b', null, done ? '#' + x.rank : '·'), h('span', { class: 'nm' }, x.name),
      h('span', { class: 'muted' }, done ? x.correct + '/' + x.total : (s.status === 'playing' ? 'đang chơi' : 'sẵn sàng')));
    if (hostMode && s.status !== 'ended') li.appendChild(h('button', { class: 'ail-btn sm', 'aria-label': 'Mời ' + x.name + ' ra khỏi phòng', onclick: function () { api('POST', '/' + code + '/kick', { member_id: x.id }).then(poll); } }, 'Mời ra'));
    ul.appendChild(li);
  });
  return ul;
}
function copy(text, btn) { if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { btn.textContent = 'Đã chép'; setTimeout(function () { btn.textContent = 'Chép liên kết'; }, 1500); }); }

function render(s) {
  var title = h('h1', null, s.app.name);
  var kids = [title];
  if (s.host) {
    var link = location.origin + '/room/' + s.code, cp = h('button', { class: 'ail-btn sm', onclick: function () { copy(link, cp); } }, 'Chép liên kết');
    kids.push(h('div', { class: 'card' }, h('div', { class: 'muted' }, 'Mã phòng — chủ phòng'), h('div', { class: 'code' }, s.code),
      h('div', { class: 'row' }, h('span', { class: 'muted' }, link), cp)));
    var acts = h('div', { class: 'row' });
    if (s.status === 'lobby') acts.appendChild(h('button', { class: 'ail-btn pri', onclick: function () { api('POST', '/' + code + '/start').then(poll).catch(function (e) { msg(e.message, true); }); } }, 'Bắt đầu (' + s.members.length + ' người)'));
    if (s.status !== 'ended') {
      acts.appendChild(h('a', { class: 'ail-btn', href: '/play/0?room=' + s.code, target: '_blank' }, 'Chơi thử'));
      acts.appendChild(h('button', { class: 'ail-btn', onclick: function () { if (confirm('Kết thúc phòng? Không ai gửi thêm điểm được nữa.')) api('POST', '/' + code + '/end').then(poll); } }, 'Kết thúc phòng'));
    }
    acts.appendChild(h('a', { class: 'ail-btn', href: '/' }, 'Về AI Lab'));
    kids.push(h('div', { class: 'card' }, h('div', null, h('b', null, s.status === 'lobby' ? 'Đang chờ người vào' : s.status === 'playing' ? 'Đang chơi' : 'Đã kết thúc')), acts, h('p', { class: 'msg muted' })));
    kids.push(h('div', { class: 'card' }, h('b', null, 'Thành viên & điểm'), memberList(s, true)));
  } else if (!s.me) {
    if (s.status === 'ended') { kids.push(h('div', { class: 'card' }, h('p', null, 'Phòng này đã kết thúc.'), h('a', { class: 'ail-btn', href: '/room' }, 'Vào phòng khác'))); }
    else {
      var inp = h('input', { placeholder: 'Biệt danh của bạn', maxlength: '20', 'aria-label': 'Biệt danh', autocomplete: 'off', value: nameDraft });
      inp.addEventListener('input', function () { nameDraft = inp.value; });
      var go = function () { api('POST', '/' + code + '/join', { name: inp.value }).then(function (d) { localStorage.setItem(KEY, d.token); poll(); }).catch(function (e) { msg(e.message, true); }); };
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
      kids.push(h('div', { class: 'card' }, h('p', { class: 'muted' }, 'Phòng ' + s.code + ' · ' + s.members.length + ' người đã vào. Chọn một biệt danh để tham gia.'),
        h('div', { class: 'row' }, inp, h('button', { class: 'ail-btn pri', onclick: go }, 'Vào phòng')), h('p', { class: 'msg muted' }),
        h('p', { class: 'muted' }, 'Là chủ phòng? ', h('a', { href: '/' }, 'Đăng nhập'), ' rồi mở lại liên kết này.')));
    }
  } else {
    var mine = s.members.filter(function (x) { return x.id === s.me.id; })[0];
    var done = mine && mine.finished != null;
    var text = s.status === 'ended' ? 'Phòng đã kết thúc.' : s.status === 'lobby' ? 'Chờ chủ phòng bắt đầu… Bạn vào với tên “' + s.me.name + '”.' : done ? 'Bạn đã chơi xong: ' + mine.correct + '/' + mine.total + '.' : 'Bắt đầu rồi! Đang mở trò chơi…';
    var card = h('div', { class: 'card' }, h('b', null, text));
    if (s.status === 'playing' && !done) card.appendChild(h('a', { class: 'ail-btn pri', href: '/play/0?room=' + s.code }, 'Vào chơi'));
    kids.push(card, h('div', { class: 'card' }, h('b', null, 'Bảng xếp hạng'), memberList(s, false)));
    if (s.status === 'playing' && !done && !redirected) { redirected = true; location.href = '/play/0?room=' + s.code; }
  }
  var keep = root.querySelector('input'), had = keep && document.activeElement === keep;
  root.replaceChildren.apply(root, kids);
  if (had) { var ni = root.querySelector('input'); if (ni) { ni.focus(); ni.setSelectionRange(ni.value.length, ni.value.length); } }
}

function poll() {
  if (busy) return Promise.resolve();
  busy = true;
  return api('GET', '/' + code).then(function (s) { last = JSON.stringify(s.members) + s.status + s.role; render(s); }).catch(function (e) {
    if (e.code === 'no_room') { clearInterval(timer); root.replaceChildren(h('h1', null, 'Không thấy phòng'), h('div', { class: 'card' }, h('p', null, e.message), h('a', { class: 'ail-btn', href: '/room' }, 'Nhập mã khác'))); }
    else msg('Mất kết nối, đang thử lại…', true);
  }).then(function () { busy = false; });
}
if (!code) joinByCode();
else { poll(); timer = setInterval(function () { if (!document.activeElement || document.activeElement.tagName !== 'INPUT' || !document.activeElement.value) poll(); }, 2500); }
})();
