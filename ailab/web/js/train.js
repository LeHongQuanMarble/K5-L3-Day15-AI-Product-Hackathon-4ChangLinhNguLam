/* Trang Train mô hình (Hình ảnh · Tư thế) — làm giống AI Lab của learning:
 * người dùng tải ảnh / chụp webcam và chia lớp ngay trên trang này; việc HUẤN LUYỆN thì AI Lab nhờ trang train của Teachable Machine
 * (Chrome không giao diện điều khiển ở máy chủ, xem ailab/train_worker). Xong, mô hình tự có trong danh sách (riêng tư),
 * người dùng vào sửa để gán vai trò cho từng lớp. */
import { h, api, ico, btn, errBox, toast } from './dom.js';

var MIN = 10, MAX = 300, MAX_CLASSES = 8, MAX_SIDE = 320, TOTAL_CAP = 60 * 1024 * 1024;
var KIND = {
  image: { label: 'Hình ảnh', hint: 'Mỗi lớp là một hành động học sinh làm trước camera, tên viết không dấu (Gio tay phai). Chụp thân người rõ, nhiều góc.' },
  pose: { label: 'Tư thế', hint: 'Mỗi lớp là một tư thế cơ thể (Gio tay phai). Ảnh cần thấy cả người; Teachable Machine đọc các điểm trên cơ thể.' }
};

function plain(s) { return s.normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd').replace(/Đ/g, 'D'); }
function mb(n) { return (n / 1048576).toFixed(1) + ' MB'; }

/* Thu nhỏ ảnh trong trình duyệt (cạnh dài tối đa 320px, JPEG) để gửi nhẹ; trả {uri, bytes}. */
function shrink(src, mirror) {
  var w = src.videoWidth || src.naturalWidth || src.width, hh = src.videoHeight || src.naturalHeight || src.height;
  var k = Math.min(1, MAX_SIDE / Math.max(w, hh));
  var cv = document.createElement('canvas'); cv.width = Math.max(1, Math.round(w * k)); cv.height = Math.max(1, Math.round(hh * k));
  var cx = cv.getContext('2d');
  if (mirror) { cx.translate(cv.width, 0); cx.scale(-1, 1); }
  cx.drawImage(src, 0, 0, cv.width, cv.height);
  var uri = cv.toDataURL('image/jpeg', 0.85);
  return { uri: uri, bytes: Math.round(uri.length * 0.75) };
}
function fileToImage(file) {
  return new Promise(function (ok, no) {
    var u = URL.createObjectURL(file), im = new Image();
    im.onload = function () { URL.revokeObjectURL(u); ok(im); };
    im.onerror = function () { URL.revokeObjectURL(u); no(new Error('Không đọc được ảnh ' + file.name)); };
    im.src = u;
  });
}

export function trainPage(ctx, kind) {
  if (!KIND[kind]) { location.hash = '#/models/new'; return; }
  var root = h('div', { class: 'ail-train' });
  ctx.mount(root);
  var poll = null;
  var state = { name: '', description: '', classes: [], epochs: '', batch: '', lr: '' };
  function newClass(n) { return { name: n || '', imgs: [] }; }
  state.classes = [newClass('Lop 1'), newClass('Lop 2')];
  function totalBytes() { return state.classes.reduce(function (a, c) { return a + c.imgs.reduce(function (b, i) { return b + i.bytes; }, 0); }, 0); }

  /* có việc đang chạy thì hiện tiến độ thay vì form */
  api('GET', '/api/train').then(function (d) {
    var live = (d.jobs || []).filter(function (j) { return j.status === 'queued' || j.status === 'running'; })[0];
    if (live) progress(live); else form();
  }).catch(function (e) { root.replaceChildren(errBox(e)); });

  function form() {
    stopPoll();
    var msg = h('div'), trainBtn;
    var cam = { stream: null, owner: null };
    function stopCam() { if (cam.stream) cam.stream.getTracks().forEach(function (t) { t.stop(); }); cam.stream = null; cam.owner = null; }
    function redraw() { stopCam(); form(); }

    function classCard(c, idx) {
      var count = h('span', { class: 'meta' });
      var grid = h('div', { class: 'ail-tr-grid' });
      var warn = h('div', { class: 'meta' });
      var nameIn = h('input', { type: 'text', maxlength: 60, value: c.name, 'aria-label': 'Tên lớp ' + (idx + 1), placeholder: 'Hành động, viết không dấu: Gio tay phai' });
      function refresh() {
        var ok = c.imgs.length >= MIN;
        count.textContent = c.imgs.length + ' ảnh' + (ok ? '' : ' · cần thêm ' + (MIN - c.imgs.length) + ' ảnh (tối thiểu ' + MIN + ')');
        count.style.color = ok ? '' : 'var(--jl-status-warning-strong)';
        grid.replaceChildren.apply(grid, c.imgs.slice(-24).map(function (i) { return h('img', { src: i.uri, alt: '', class: 'ail-tr-th' }); }));
        warn.replaceChildren();
        if (plain(c.name) !== c.name) warn.replaceChildren('Tên lớp nên viết không dấu: ' + plain(c.name) + ' ', h('button', { type: 'button', class: 'ail-btn sm', onclick: function () { c.name = plain(c.name); nameIn.value = c.name; refresh(); } }, 'Bỏ dấu'));
        updateTrain();
      }
      nameIn.oninput = function () { c.name = nameIn.value; refresh(); };
      function add(list) {
        var room = MAX - c.imgs.length;
        list.slice(0, room).forEach(function (r) { c.imgs.push(r); });
        if (list.length > room) toast('Mỗi lớp tối đa ' + MAX + ' ảnh; phần thừa bị bỏ.', 'err');
        refresh();
      }
      var file = h('input', { type: 'file', accept: 'image/jpeg,image/png,image/webp', multiple: true, style: 'display:none', 'aria-label': 'Tải ảnh cho lớp ' + (idx + 1), onchange: function () {
        var fs = [].slice.call(file.files); file.value = '';
        var done = [];
        fs.reduce(function (p, f) { return p.then(function () { return fileToImage(f).then(function (im) { done.push(shrink(im, false)); }).catch(function () {}); }); }, Promise.resolve())
          .then(function () { if (fs.length && !done.length) toast('Không đọc được ảnh nào (dùng JPEG, PNG hoặc WebP).', 'err'); add(done); });
      } });
      var camBox = h('div', { class: 'ail-tr-cam' });
      function camToggle() {
        if (cam.owner === c) { stopCam(); camBox.replaceChildren(); return; }
        stopCam(); document.querySelectorAll('.ail-tr-cam').forEach(function (b) { b.replaceChildren(); });
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { toast('Trình duyệt không cho dùng webcam (cần https hoặc localhost).', 'err'); return; }
        navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false }).then(function (s) {
          cam.stream = s; cam.owner = c;
          var v = h('video', { autoplay: true, playsinline: true, class: 'ail-tr-video' }); v.muted = true; v.srcObject = s; v.play();
          var timer = null;
          function snap() { if (v.videoWidth && c.imgs.length < MAX) { c.imgs.push(shrink(v, true)); refresh(); } }
          var hold = h('button', { type: 'button', class: 'ail-btn pri', 'aria-label': 'Giữ để chụp liên tục' }, ico('camera'), 'Giữ để chụp');
          hold.onpointerdown = function (e) { e.preventDefault(); snap(); timer = setInterval(snap, 120); };
          ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (ev) { hold.addEventListener(ev, function () { clearInterval(timer); timer = null; }); });
          camBox.replaceChildren(v, hold);
        }).catch(function (e) {
          toast(e && e.name === 'NotAllowedError' ? 'Bạn chưa cho phép dùng webcam.' : 'Không bật được webcam: ' + ((e && e.message) || e), 'err');
        });
      }
      var card = h('div', { class: 'ail-tr-card' },
        h('div', { class: 'row' }, h('div', { class: 'grow' }, nameIn),
          state.classes.length > 2 ? h('button', { type: 'button', class: 'ail-btn sm bad', 'aria-label': 'Xoá lớp ' + (idx + 1), onclick: function () { state.classes.splice(idx, 1); redraw(); } }, ico('trash')) : null),
        warn, count, grid,
        h('div', { class: 'row' },
          h('button', { type: 'button', class: 'ail-btn', onclick: function () { file.click(); } }, ico('plus'), 'Tải ảnh'), file,
          h('button', { type: 'button', class: 'ail-btn', onclick: camToggle }, ico('camera'), 'Webcam'),
          c.imgs.length ? h('button', { type: 'button', class: 'ail-btn', onclick: function () { c.imgs = []; refresh(); } }, 'Xoá hết ảnh') : null),
        camBox);
      refresh();
      return card;
    }

    var name = h('input', { type: 'text', maxlength: 80, value: state.name, placeholder: 'Ví dụ: Đáp án A–D', 'aria-label': 'Tên mô hình', oninput: function (e) { state.name = e.target.value; updateTrain(); } });
    var desc = h('textarea', { maxlength: 300, style: 'min-height:60px', 'aria-label': 'Mô tả mô hình' }); desc.value = state.description; desc.oninput = function () { state.description = desc.value; };
    function sel(key, label, opts, def) {
      var s = h('select', { 'aria-label': label, onchange: function (e) { state[key] = e.target.value; } },
        opts.map(function (o) { return h('option', { value: String(o), selected: String(state[key] || def) === String(o) }, String(o) + (String(o) === String(def) ? ' (mặc định)' : '')); }));
      return h('label', { class: 'l' }, label, s);
    }
    var epochs = h('input', { type: 'number', min: 1, max: 500, value: state.epochs || 50, 'aria-label': 'Epochs', onchange: function (e) { state.epochs = e.target.value; } });
    var adv = h('details', { class: 'ail-tr-adv' }, h('summary', null, 'Nâng cao (mặc định của Teachable Machine)'),
      h('div', { class: 'row' },
        h('label', { class: 'l' }, 'Epochs', epochs),
        sel('batch', 'Batch size', [16, 32, 64, 128, 256, 512], 16),
        sel('lr', 'Learning rate', [0.00001, 0.0001, 0.001, 0.003, 0.01], 0.001)));
    var addBtn = h('button', { type: 'button', class: 'ail-btn', onclick: function () { state.classes.push(newClass('Lop ' + (state.classes.length + 1))); redraw(); } }, ico('plus'), 'Thêm lớp');
    if (state.classes.length >= MAX_CLASSES) addBtn.disabled = true;
    var summary = h('div', { class: 'meta', 'aria-live': 'polite' });
    trainBtn = h('button', { type: 'button', class: 'ail-btn pri lg', onclick: send }, ico('wand'), 'Train mô hình');
    function problems() {
      var p = [];
      if (!state.name.trim()) p.push('Đặt tên mô hình.');
      var names = state.classes.map(function (c) { return c.name.trim().toLowerCase(); });
      if (names.some(function (n) { return !n; })) p.push('Mỗi lớp cần một tên.');
      else if (names.some(function (n, i) { return names.indexOf(n) !== i; })) p.push('Tên lớp không được trùng nhau.');
      state.classes.forEach(function (c) { if (c.imgs.length < MIN) p.push('Lớp “' + (c.name || '…') + '” cần ít nhất ' + MIN + ' ảnh.'); });
      if (totalBytes() > TOTAL_CAP) p.push('Tổng ảnh quá lớn (' + mb(totalBytes()) + ' / ' + mb(TOTAL_CAP) + '). Bớt ảnh.');
      return p;
    }
    function updateTrain() {
      var p = problems();
      trainBtn.disabled = p.length > 0;
      summary.textContent = p.length ? p[0] : 'Sẵn sàng: ' + state.classes.length + ' lớp, ' + state.classes.reduce(function (a, c) { return a + c.imgs.length; }, 0) + ' ảnh (' + mb(totalBytes()) + ').';
    }
    function send() {
      var p = problems(); if (p.length) { msg.replaceChildren(errBox({ message: p[0] })); return; }
      trainBtn.disabled = true; msg.replaceChildren();
      var settings = {};
      if (state.epochs && +state.epochs !== 50) settings.epochs = +state.epochs;
      if (state.batch && +state.batch !== 16) settings.batch_size = +state.batch;
      if (state.lr && +state.lr !== 0.001) settings.learning_rate = +state.lr;
      api('POST', '/api/train', { kind: kind, name: state.name, description: state.description, settings: settings,
        classes: state.classes.map(function (c) { return { name: c.name.trim(), images: c.imgs.map(function (i) { return i.uri; }) }; }) })
        .then(function (d) { stopCam(); progress(d.job); })
        .catch(function (x) { msg.replaceChildren(errBox(x)); trainBtn.disabled = false; updateTrain(); });
    }
    root.replaceChildren(h('div', { class: 'ail-form' },
      h('h2', null, 'Train mô hình ' + KIND[kind].label.toLowerCase()),
      h('div', { class: 'note' }, h('strong', null, 'Cách làm. '), '1) Chia lớp và thêm ảnh ở đây (tải ảnh hoặc chụp webcam). 2) Bấm Train: AI Lab nhờ Teachable Machine huấn luyện giúp, mất khoảng 20–60 giây. 3) Xong, mô hình có trong danh sách; vào sửa để gán vai trò cho từng lớp. ' + KIND[kind].hint),
      h('label', { class: 'l' }, 'Tên mô hình', name),
      h('label', { class: 'l' }, 'Mô tả (không bắt buộc)', desc),
      h('strong', null, 'Các lớp'),
      h('div', { class: 'ail-tr-cards' }, state.classes.map(classCard)),
      h('div', null, addBtn),
      adv, summary, msg,
      h('div', { class: 'row' }, trainBtn, h('a', { class: 'ail-btn', href: '#/models/new' }, 'Quay lại'))));
    updateTrain();
  }

  function stopPoll() { if (poll) { clearInterval(poll); poll = null; } }
  function progress(job) {
    stopPoll();
    var body = h('div'), t0 = Date.now();
    function draw(j) {
      var kids = [];
      if (j.status === 'queued') {
        kids.push(h('p', null, ico('refresh'), ' Đang xếp hàng' + (j.queued ? ' (còn ' + j.queued + ' việc phía trước)' : '') + '…'));
        kids.push(h('p', { class: 'meta' }, 'Mỗi lần AI Lab train một mô hình. Bạn có thể rời trang, việc vẫn chạy.'));
      } else if (j.status === 'running') {
        kids.push(h('p', null, ico('refresh'), ' Teachable Machine đang huấn luyện “' + j.name + '” (' + j.classes.join(', ') + ')…'));
        kids.push(h('p', { class: 'meta' }, 'Đã chờ ' + Math.round((Date.now() - t0) / 1000) + ' giây. Thường xong trong 20–90 giây, tối đa 7 phút.'));
      } else if (j.status === 'done') {
        kids.push(h('p', null, ico('check'), ' Đã train xong và lưu mô hình “' + j.name + '”.'));
        kids.push(h('p', { class: 'meta' }, 'Đường dẫn Teachable Machine: ', h('a', { href: j.url, target: '_blank', rel: 'noopener' }, j.url)));
        kids.push(h('div', { class: 'row' }, btn('Gán vai trò cho các lớp', 'edit', { cls: 'pri', href: '#/models/' + j.model_id }), btn('Xem danh sách mô hình', 'cube', { href: '#/models' }),
          h('button', { class: 'ail-btn', type: 'button', onclick: function () { state.classes = [newClass('Lop 1'), newClass('Lop 2')]; state.name = ''; form(); } }, 'Train mô hình khác')));
      } else {
        kids.push(errBox({ message: j.error || 'Train không thành công.' }));
        kids.push(h('div', { class: 'row' }, h('button', { class: 'ail-btn pri', type: 'button', onclick: function () { form(); } }, 'Quay lại chỉnh và gửi lại')));
      }
      if (j.status === 'queued' || j.status === 'running') {
        kids.push(h('div', { class: 'row' }, h('button', { class: 'ail-btn bad', type: 'button', onclick: function () {
          api('POST', '/api/train/' + j.id + '/cancel').then(function () { tick(); }).catch(function (e) { toast(e.message, 'err'); });
        } }, 'Huỷ')));
      }
      body.replaceChildren.apply(body, kids);
    }
    function tick() {
      api('GET', '/api/train/' + job.id).then(function (d) {
        draw(d.job);
        if (d.job.status !== 'queued' && d.job.status !== 'running') { stopPoll(); if (d.job.status === 'done') toast('Train xong, đã lưu mô hình.', 'ok'); }
      }).catch(function (e) { stopPoll(); body.replaceChildren(errBox(e)); });
    }
    root.replaceChildren(h('div', { class: 'ail-form' }, h('h2', null, 'Train mô hình ' + KIND[kind].label.toLowerCase()), body));
    draw(job);
    poll = setInterval(function () { if (!document.body.contains(root)) return stopPoll(); tick(); }, 2000);
  }
}
