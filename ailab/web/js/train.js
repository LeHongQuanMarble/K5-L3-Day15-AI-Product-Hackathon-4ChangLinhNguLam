/* Trang Train mô hình (Hình ảnh · Tư thế · Âm thanh) — bố cục và cách làm giống AI Lab của learning:
 * cột lớp (tải ảnh / chụp camera) → thẻ Huấn luyện → thẻ Xem thử, nối bằng đường mảnh. Việc HUẤN LUYỆN thì AI Lab nhờ trang train của
 * Teachable Machine (Chrome không giao diện ở máy chủ, xem ailab/train_worker). Xong, mô hình tự có trong danh sách (riêng tư).
 * Ba loại dùng chung các bộ phận ở train-parts.js; chỗ khác nhau chỉ nằm trong bảng KINDS dưới đây. */
import { h, api, ico, btn, errBox, toast } from './dom.js';
import { showIntro } from './motion-intro.js';
import { classCard, previewCard, panel, wires, mb } from './train-parts.js';

var NOISE = 'Background Noise', MAX_SIDE = 320, TOTAL_CAP = 60 * 1024 * 1024;
var TF = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js';
var PHOTO_HINT = 'Mỗi lớp là một hành động học sinh làm trước camera, tên viết không dấu (Gio tay phai). Train xong, bạn gán mỗi hành động với một đáp án, ví dụ Gio tay phai → A.';
var KINDS = {
  image: { kind: 'image', label: 'Hình ảnh', unit: 'ảnh', accept: 'image/jpeg,image/png,image/webp', max: 150, hint: PHOTO_HINT,
    examples: ['Gio tay phai', 'Gio tay trai', 'Hai tay len dau', 'Khoanh tay'], extra: 'Khong co nguoi',
    libs: [TF, 'https://cdn.jsdelivr.net/npm/@teachablemachine/image@0.8/dist/teachablemachine-image.min.js'],
    min: function () { return 10; }, fileText: function () { return 'JPG hoặc PNG, tối thiểu 10 ảnh, tối đa 150 ảnh'; } },
  pose: { kind: 'pose', label: 'Tư thế', unit: 'ảnh', accept: 'image/jpeg,image/png,image/webp', max: 150, hint: PHOTO_HINT,
    examples: ['Gio tay phai', 'Gio tay trai', 'Hai tay len dau', 'Khoanh tay'], extra: 'Khong co nguoi',
    libs: [TF, 'https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js'],
    min: function () { return 10; }, fileText: function () { return 'JPG hoặc PNG, tối thiểu 10 ảnh, tối đa 150 ảnh. Ảnh cần thấy cả người.'; } },
  audio: { kind: 'audio', audio: true, label: 'Âm thanh', unit: 'mẩu', accept: 'audio/*', max: 60,
    hint: 'Mỗi lớp là một âm thanh học sinh tạo ra (vỗ tay, huýt sáo), tên viết không dấu (Vo tay). Lớp Background Noise (tiếng nền lúc yên tĩnh) luôn có. Train xong, bạn gán mỗi âm thanh với một đáp án.',
    examples: ['Vo tay', 'Huyt sao'], libs: [TF, 'https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@0.4.0/dist/speech-commands.min.js'],
    min: function (c) { return c.fixed ? 20 : 8; }, fileText: function (c) { return 'Mỗi mẩu dài 1 giây. Tối thiểu ' + (c.fixed ? 20 : 8) + ' mẩu, tối đa 60.'; } }
};

/* ---- ảnh: thu nhỏ trong trình duyệt (cạnh dài tối đa 320px, JPEG) ---- */
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
/* ---- âm thanh: cắt thành các mẩu WAV 1 giây (16-bit, mono) ---- */
function wavOf(samples, rate) {
  var n = samples.length, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
  function s(o, str) { for (var i = 0; i < str.length; i++) v.setUint8(o + i, str.charCodeAt(i)); }
  s(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); s(8, 'WAVE'); s(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); s(36, 'data'); v.setUint32(40, n * 2, true);
  for (var i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, samples[i])) * 32767, true);
  return new Uint8Array(buf);
}
function b64(u8) { var s = '', k = 0x8000; for (var i = 0; i < u8.length; i += k) s += String.fromCharCode.apply(null, u8.subarray(i, i + k)); return btoa(s); }
function clipsOf(audioBuf, maxClips) {
  var rate = audioBuf.sampleRate, len = audioBuf.length, ch = audioBuf.numberOfChannels, mono = new Float32Array(len);
  for (var c = 0; c < ch; c++) { var d = audioBuf.getChannelData(c); for (var i = 0; i < len; i++) mono[i] += d[i] / ch; }
  var out = [];
  for (var at = 0; at + rate <= len && out.length < maxClips; at += rate) {
    var uri = 'data:audio/wav;base64,' + b64(wavOf(mono.subarray(at, at + rate), rate));
    out.push({ uri: uri, bytes: Math.round(uri.length * 0.75) });
  }
  return out;
}
function decode(arrayBuffer) {
  var AC = window.AudioContext || window.webkitAudioContext, ac = new AC();
  return ac.decodeAudioData(arrayBuffer).then(function (b) { ac.close(); return b; });
}

export function trainPage(ctx, kind) {
  var cfg = KINDS[kind];
  if (!cfg) { location.hash = '#/models'; return; }
  var root = h('div', { class: 'ail-train' });
  ctx.mount(root);
  var poll = null, cam = { stream: null, owner: null };
  var state = { name: '', description: '', consent: false, classes: fresh(), epochs: '', batch: '', lr: '', open: false };
  function fresh() { return cfg.audio ? [{ name: NOISE, imgs: [], fixed: true }, { name: '', imgs: [] }] : [{ name: '', imgs: [] }, { name: '', imgs: [] }]; }
  function stopCam() { if (cam.stream) cam.stream.getTracks().forEach(function (t) { t.stop(); }); cam.stream = null; cam.owner = null; }
  function stopPoll() { if (poll) { clearInterval(poll); poll = null; } }
  var preview = previewCard(cfg);

  api('GET', '/api/train').then(function (d) {
    var live = (d.jobs || []).filter(function (j) { return j.status === 'queued' || j.status === 'running'; })[0];
    draw(live || null);
  }).catch(function (e) { root.replaceChildren(errBox(e)); });

  function totalBytes() { return state.classes.reduce(function (a, c) { return a + c.imgs.reduce(function (b, i) { return b + i.bytes; }, 0); }, 0); }
  function problems() {
    var p = [];
    if (!state.name.trim()) p.push('Đặt tên cho mô hình.');
    var names = state.classes.map(function (c) { return c.name.trim().toLowerCase(); });
    if (names.some(function (n) { return !n; })) p.push('Mỗi lớp cần một tên.');
    else if (names.some(function (n, i) { return names.indexOf(n) !== i; })) p.push('Tên lớp không được trùng nhau.');
    if (cfg.audio && names.indexOf(NOISE.toLowerCase(), 1) > 0) p.push('Tên “' + NOISE + '” dành riêng cho lớp tiếng nền.');
    state.classes.forEach(function (c) { if (c.imgs.length < cfg.min(c)) p.push('Lớp “' + (c.name || '…') + '” cần ít nhất ' + cfg.min(c) + ' ' + cfg.unit + '.'); });
    if (totalBytes() > TOTAL_CAP) p.push('Tổng dung lượng quá lớn (' + mb(totalBytes()) + ' / ' + mb(TOTAL_CAP) + '). Bớt đi.');
    if (!state.consent) p.push('Tick xác nhận bản quyền ảnh và đường dẫn công khai.');
    return p;
  }

  /* ---- thao tác của thẻ lớp ---- */
  var cards = [], trainBtn, hint, sum;
  function update() {
    var p = problems();
    if (trainBtn) trainBtn.disabled = p.length > 0;
    if (hint) hint.textContent = p.length ? p[0] : 'Sẵn sàng: ' + state.classes.length + ' lớp, ' + state.classes.reduce(function (a, c) { return a + c.imgs.length; }, 0) + ' ' + cfg.unit + ' (' + mb(totalBytes()) + ').';
  }
  function refreshAll() { cards.forEach(function (k) { k.refresh(); }); update(); }
  var ops = {
    rename: function (c, v) { c.name = v; update(); },
    clear: function (c) { c.imgs = []; refreshAll(); },
    remove: function (c) { state.classes.splice(state.classes.indexOf(c), 1); stopCam(); draw(null, true); },
    add: function (c, files) {
      var done = [];
      files.reduce(function (p, f) {
        return p.then(function () {
          if (cfg.audio) return f.arrayBuffer().then(decode).then(function (b) { clipsOf(b, cfg.max).forEach(function (r) { done.push(r); }); }).catch(function () {});
          return fileToImage(f).then(function (im) { done.push(shrink(im, false)); }).catch(function () {});
        });
      }, Promise.resolve()).then(function () {
        if (files.length && !done.length) toast(cfg.audio ? 'Không đọc được âm thanh nào (mỗi file cần dài ít nhất 1 giây).' : 'Không đọc được ảnh nào (dùng JPEG, PNG hoặc WebP).', 'err');
        var room = cfg.max - c.imgs.length;
        done.slice(0, room).forEach(function (r) { c.imgs.push(r); });
        if (done.length > room) toast('Mỗi lớp tối đa ' + cfg.max + ' ' + cfg.unit + '; phần thừa bị bỏ.', 'err');
        refreshAll();
      });
    },
    capture: function (c, box) { return cfg.audio ? micRecord(c, box) : camToggle(c, box); }
  };
  function camToggle(c, box) {
    if (cam.owner === c) { stopCam(); box.replaceChildren(); return; }
    stopCam(); document.querySelectorAll('.ail-tr-cam').forEach(function (b) { b.replaceChildren(); });
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { toast('Trình duyệt không cho dùng camera (cần https hoặc localhost).', 'err'); return; }
    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false }).then(function (s) {
      cam.stream = s; cam.owner = c;
      var v = h('video', { autoplay: true, playsinline: true, class: 'ail-tr-video' }); v.muted = true; v.srcObject = s; v.play();
      var timer = null;
      function snap() { if (v.videoWidth && c.imgs.length < cfg.max) { c.imgs.push(shrink(v, true)); refreshAll(); } }
      var hold = h('button', { type: 'button', class: 'ail-btn pri', 'aria-label': 'Giữ để chụp liên tục' }, ico('camera'), 'Giữ để chụp');
      hold.onpointerdown = function (e) { e.preventDefault(); snap(); timer = setInterval(snap, 120); };
      ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (ev) { hold.addEventListener(ev, function () { clearInterval(timer); timer = null; }); });
      box.replaceChildren(v, hold);
    }).catch(function (e) {
      toast(e && e.name === 'NotAllowedError' ? 'Bạn chưa cho phép dùng camera.' : 'Không bật được camera: ' + ((e && e.message) || e), 'err');
    });
  }
  function micRecord(c, box) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) { toast('Trình duyệt không cho thu âm (cần https hoặc localhost).', 'err'); return; }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
      var left = c.fixed ? 12 : 8, chunks = [], rec = new MediaRecorder(s), tm;
      var info = h('span', { class: 'meta' }, 'Đang thu ' + left + ' giây…');
      box.replaceChildren(info, h('button', { type: 'button', class: 'ail-btn bad', onclick: function () { rec.stop(); } }, 'Dừng'));
      rec.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); };
      rec.onstop = function () {
        clearInterval(tm); s.getTracks().forEach(function (t) { t.stop(); }); box.replaceChildren();
        new Blob(chunks).arrayBuffer().then(decode).then(function (b) {
          var cl = clipsOf(b, cfg.max - c.imgs.length); if (!cl.length) toast('Bản thu ngắn hơn 1 giây.', 'err');
          cl.forEach(function (r) { c.imgs.push(r); }); refreshAll();
        }).catch(function () { toast('Không đọc được bản thu.', 'err'); });
      };
      rec.start(); tm = setInterval(function () { left--; info.textContent = 'Đang thu ' + left + ' giây…'; if (left <= 0) rec.stop(); }, 1000);
    }).catch(function (e) { toast(e && e.name === 'NotAllowedError' ? 'Bạn chưa cho phép dùng micro.' : 'Không bật được micro: ' + ((e && e.message) || e), 'err'); });
  }

  /* ---- thẻ Huấn luyện ---- */
  function trainBody() {
    var msg = h('div');
    var name = h('input', { type: 'text', maxlength: 80, value: state.name, placeholder: 'Ví dụ: Đáp án A–D', 'aria-label': 'Tên mô hình', oninput: function (e) { state.name = e.target.value; update(); } });
    var consent = h('input', { type: 'checkbox', checked: state.consent, id: 'tb-consent', onchange: function (e) { state.consent = e.target.checked; update(); } });
    function sel(key, label, opts, def) {
      return h('label', { class: 'l' }, label, h('select', { 'aria-label': label, onchange: function (e) { state[key] = e.target.value; } },
        opts.map(function (o) { return h('option', { value: String(o), selected: String(state[key] || def) === String(o) }, String(o) + (String(o) === String(def) ? ' (mặc định)' : '')); })));
    }
    var desc = h('textarea', { maxlength: 300, style: 'min-height:56px', 'aria-label': 'Mô tả mô hình' }); desc.value = state.description; desc.oninput = function () { state.description = desc.value; };
    var adv = h('details', { class: 'ail-tb-adv', open: state.open, ontoggle: function (e) { state.open = e.target.open; } },
      h('summary', null, 'Nâng cao', h('span', { class: 'ail-tb-chev' }, '⌄')),
      h('div', { class: 'ail-tb-advbody' },
        h('label', { class: 'l' }, 'Mô tả (không bắt buộc)', desc),
        cfg.audio ? h('p', { class: 'meta' }, 'Teachable Machine dùng thiết lập mặc định cho mô hình âm thanh.') : h('div', { class: 'row' },
          h('label', { class: 'l' }, 'Epochs', h('input', { type: 'number', min: 1, max: 500, value: state.epochs || 50, 'aria-label': 'Epochs', onchange: function (e) { state.epochs = e.target.value; } })),
          sel('batch', 'Batch size', [16, 32, 64, 128, 256, 512], 16), sel('lr', 'Learning rate', [0.00001, 0.0001, 0.001, 0.003, 0.01], 0.001))));
    trainBtn = h('button', { type: 'button', class: 'ail-tb-train-btn', onclick: send }, ico('wand'), 'Train mô hình');
    hint = h('div', { class: 'ail-tb-hint', 'aria-live': 'polite' });
    var wrap = h('div', { class: 'ail-tb-trainbody' },
      h('label', { class: 'l' }, 'Tên mô hình', name),
      h('label', { class: 'ail-tb-consent', for: 'tb-consent' }, consent, h('span', null, 'Tôi có quyền dùng các ' + (cfg.audio ? 'âm thanh' : 'ảnh') + ' này và hiểu mô hình ở đường dẫn công khai.')),
      trainBtn, hint, msg, adv);
    function send() {
      var p = problems(); if (p.length) { msg.replaceChildren(errBox({ message: p[0] })); return; }
      trainBtn.disabled = true; msg.replaceChildren();
      var settings = {};
      if (!cfg.audio) {
        if (state.epochs && +state.epochs !== 50) settings.epochs = +state.epochs;
        if (state.batch && +state.batch !== 16) settings.batch_size = +state.batch;
        if (state.lr && +state.lr !== 0.001) settings.learning_rate = +state.lr;
      }
      api('POST', '/api/train', { kind: kind, name: state.name, description: state.description, settings: settings,
        classes: state.classes.map(function (c) { var u = c.imgs.map(function (i) { return i.uri; }); return cfg.audio ? { name: c.name.trim(), sounds: u } : { name: c.name.trim(), images: u }; }) })
        .then(function (d) { stopCam(); draw(d.job); })
        .catch(function (x) { msg.replaceChildren(errBox(x)); update(); });
    }
    return wrap;
  }
  function progressBody(job) {
    stopPoll();
    var body = h('div', { class: 'ail-tb-trainbody' }), t0 = Date.now();
    function show(j) {
      var kids = [];
      if (j.status === 'queued') {
        kids.push(h('p', null, ico('refresh'), ' Đang xếp hàng' + (j.queued ? ' (còn ' + j.queued + ' việc phía trước)' : '') + '…'));
        kids.push(h('p', { class: 'meta' }, 'Mỗi lần AI Lab train một mô hình. Bạn có thể rời trang, việc vẫn chạy.'));
        preview.working();
      } else if (j.status === 'running') {
        kids.push(h('p', null, ico('refresh'), ' Teachable Machine đang huấn luyện “' + j.name + '” (' + j.classes.join(', ') + ')…'));
        kids.push(h('p', { class: 'meta' }, 'Đã chờ ' + Math.round((Date.now() - t0) / 1000) + ' giây. ' + (cfg.audio ? 'Âm thanh mất 2–5 phút, tối đa 16 phút.' : 'Thường xong trong 20–90 giây, tối đa 7 phút.')));
        preview.working();
      } else if (j.status === 'done') {
        kids.push(h('p', null, ico('check'), ' Đã train xong và lưu mô hình “' + j.name + '”.'));
        kids.push(h('p', { class: 'meta' }, 'Đường dẫn Teachable Machine: ', h('a', { href: j.url, target: '_blank', rel: 'noopener' }, j.url)));
        kids.push(h('div', { class: 'ail-tb-actions' }, btn('Gán vai trò cho các lớp', 'edit', { cls: 'pri', href: '#/models/' + j.model_id }), btn('Xem danh sách mô hình', 'cube', { href: '#/models' }),
          h('button', { class: 'ail-btn', type: 'button', onclick: function () { state.classes = fresh(); state.name = ''; state.consent = false; preview.reset(); draw(null); } }, 'Train mô hình khác')));
        preview.ready(j);
      } else {
        kids.push(errBox({ message: j.error || 'Train không thành công.' }));
        kids.push(h('div', { class: 'ail-tb-actions' }, h('button', { class: 'ail-btn pri', type: 'button', onclick: function () { preview.reset(); draw(null); } }, 'Quay lại chỉnh và gửi lại')));
        preview.reset();
      }
      if (j.status === 'queued' || j.status === 'running') {
        kids.push(h('div', { class: 'ail-tb-actions' }, h('button', { class: 'ail-btn bad', type: 'button', onclick: function () {
          api('POST', '/api/train/' + j.id + '/cancel').then(function () { tick(); }).catch(function (e) { toast(e.message, 'err'); });
        } }, 'Huỷ')));
      }
      body.replaceChildren.apply(body, kids);
    }
    function tick() {
      api('GET', '/api/train/' + job.id).then(function (d) {
        show(d.job);
        if (d.job.status !== 'queued' && d.job.status !== 'running') { stopPoll(); if (d.job.status === 'done') toast('Train xong, đã lưu mô hình.', 'ok'); }
      }).catch(function (e) { stopPoll(); body.replaceChildren(errBox(e)); });
    }
    show(job);
    poll = setInterval(function () { if (!document.body.contains(root)) { stopPoll(); return; } tick(); }, 2000);
    return body;
  }

  /* ---- vẽ cả trang ---- */
  function draw(job, keepPreview) {
    stopPoll(); cards = [];
    if (!job && !keepPreview) preview.reset();
    var left = h('div', { class: 'ail-tb-col ail-tb-left' }, h('p', { class: 'ail-tb-intro' }, cfg.hint));
    state.classes.forEach(function (c, i) {
      var k = classCard(cfg, c, i, ops);
      if (job) { k.el.classList.add('is-locked'); k.el.querySelectorAll('input,button').forEach(function (x) { x.disabled = true; }); }
      cards.push(k); left.appendChild(k.el);
    });
    if (!job) {
      var addRow = h('div', { class: 'ail-tb-addrowbtns' },
        h('button', { type: 'button', class: 'ail-tb-addclass', disabled: state.classes.length >= 8, onclick: function () { state.classes.push({ name: '', imgs: [] }); stopCam(); draw(null, true); } }, ico('plus'), 'Thêm lớp'));
      if (cfg.extra && !state.classes.some(function (c) { return c.name === cfg.extra; })) {
        addRow.appendChild(h('button', { type: 'button', class: 'ail-tb-addclass solid', disabled: state.classes.length >= 8, onclick: function () { state.classes.push({ name: cfg.extra, imgs: [] }); stopCam(); draw(null, true); } }, ico('plus'), 'Thêm lớp ' + cfg.extra));
      }
      left.appendChild(addRow);
    }
    var mid = h('div', { class: 'ail-tb-col ail-tb-train' }, panel('wand', 'mint', 'Huấn luyện', job ? progressBody(job) : trainBody()));
    var right = h('div', { class: 'ail-tb-col ail-tb-preview' }, preview.el);
    var head = h('div', { class: 'ail-tb-top' },
      h('div', null, h('h2', null, 'Train mô hình ' + cfg.label.toLowerCase()),
        h('p', { class: 'meta' }, 'Đặt tên các lớp, tải ' + (cfg.audio ? 'âm thanh' : 'ảnh') + ' vào từng lớp, rồi bấm Train mô hình. Khi train xong, đặt kết quả cho từng lớp và lưu.')),
      cfg.kind === 'image' ? null : btn(cfg.kind === 'pose' ? 'Xem giới thiệu Aura Flow' : 'Xem giới thiệu Aura Echo', 'play', { onclick: function () { showIntro(cfg.kind); } }));
    var board = h('div', { class: 'ail-tb' }, left, mid, right);
    root.replaceChildren(head, board);
    wires(board);
    update();
  }
}
