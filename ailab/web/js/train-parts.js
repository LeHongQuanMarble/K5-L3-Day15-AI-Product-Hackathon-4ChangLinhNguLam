/* Các bộ phận dùng chung của trang Train (Hình ảnh · Tư thế · Âm thanh): thẻ lớp, thẻ Huấn luyện, thẻ Xem thử, đường nối.
 * Bố cục lấy theo trang train của learning: cột lớp bên trái → Huấn luyện ở giữa → Xem thử bên phải, nối bằng đường cong mảnh.
 * Cả ba loại dùng CHUNG các bộ phận này; chỗ khác nhau nằm hết trong bảng cấu hình KINDS của train.js. */
import { h, ico } from './dom.js';

var NS = 'http://www.w3.org/2000/svg';

export function plain(s) { return s.normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd').replace(/Đ/g, 'D'); }
export function mb(n) { return (n / 1048576).toFixed(1) + ' MB'; }

/* ---- ô icon màu ở đầu thẻ ---- */
export function badge(icon, tone) { return h('span', { class: 'ail-tb-badge tone-' + tone, 'aria-hidden': 'true' }, ico(icon)); }

/* ---- thẻ chung ---- */
export function panel(icon, tone, title, kids) {
  return h('section', { class: 'ail-tb-card', 'aria-label': title }, h('div', { class: 'ail-tb-head' }, badge(icon, tone), h('h3', null, title)), kids);
}

/* ---- thẻ lớp ----
 * cfg: bảng của loại; c: {name, imgs, fixed}; ops: {rename, add(files), clear, remove, capture(btn,box), refresh} */
export function classCard(cfg, c, idx, ops) {
  var count = h('div', { class: 'ail-tb-count' });
  var thumbs = h('div', { class: 'ail-tr-grid' });
  var warn = h('div', { class: 'meta' });
  var box = h('div', { class: 'ail-tr-cam' });
  var nameIn = h('input', { type: 'text', maxlength: 60, value: c.name, 'aria-label': 'Tên lớp ' + (idx + 1),
    placeholder: cfg.audio ? 'Âm thanh, viết không dấu: Vo tay' : 'Hành động, viết không dấu: ' + cfg.examples[idx % cfg.examples.length] });
  if (c.fixed) { nameIn.disabled = true; nameIn.title = 'Lớp tiếng nền luôn có sẵn'; }
  nameIn.oninput = function () { ops.rename(c, nameIn.value); };
  var menu = h('div', { class: 'ail-tb-menu', hidden: true },
    h('button', { type: 'button', onclick: function () { menu.hidden = true; ops.clear(c); } }, cfg.audio ? 'Xoá hết mẩu' : 'Xoá hết ảnh'),
    c.fixed ? null : h('button', { type: 'button', class: 'bad', onclick: function () { menu.hidden = true; ops.remove(c); } }, 'Xoá lớp'));
  var file = h('input', { type: 'file', accept: cfg.accept, multiple: true, style: 'display:none', 'aria-label': (cfg.audio ? 'Tải âm thanh cho lớp ' : 'Tải ảnh cho lớp ') + (idx + 1),
    onchange: function () { var fs = [].slice.call(file.files); file.value = ''; ops.add(c, fs); } });
  var drop = h('button', { type: 'button', class: 'ail-tb-drop', onclick: function () { file.click(); } },
    h('span', { class: 'ail-tb-dropico' }, ico('upload')), cfg.audio ? 'Tải âm thanh' : 'Tải ảnh');
  ['dragover', 'dragenter'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('is-over'); }); });
  ['dragleave', 'drop'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('is-over'); }); });
  drop.addEventListener('drop', function (e) { var fs = [].slice.call(e.dataTransfer.files || []); if (fs.length) ops.add(c, fs); });
  var cap = h('button', { type: 'button', class: 'ail-tb-cap', onclick: function () { ops.capture(c, box); } },
    h('span', { class: 'ail-tb-capico' }, ico(cfg.audio ? 'play' : 'camera')), cfg.audio ? 'Thu âm' : 'Chụp bằng camera');
  var el = h('div', { class: 'ail-tb-class ail-tb-card', 'data-idx': String(idx) },
    h('div', { class: 'ail-tb-classhead' }, nameIn,
      h('button', { type: 'button', class: 'ail-tb-icon', 'aria-label': 'Sửa tên lớp ' + (idx + 1), disabled: !!c.fixed, onclick: function () { nameIn.focus(); nameIn.select(); } }, ico('edit')),
      h('button', { type: 'button', class: 'ail-tb-icon', 'aria-label': 'Thêm tuỳ chọn cho lớp ' + (idx + 1), 'aria-haspopup': 'true', onclick: function () { menu.hidden = !menu.hidden; } }, ico('more')), menu),
    warn,
    h('div', { class: 'ail-tb-add' }, h('div', { class: 'ail-tb-addlabel' }, cfg.audio ? 'Thêm âm thanh:' : 'Thêm ảnh:'),
      h('div', { class: 'ail-tb-addrow' }, drop, cap, file)),
    count, h('div', { class: 'ail-tb-fine' }, cfg.fileText(c)), thumbs, box);
  function refresh() {
    var min = cfg.min(c), n = c.imgs.length, ok = n >= min;
    count.textContent = n + ' / ' + min + ' ' + cfg.unit + (ok ? '' : ' · cần thêm ' + (min - n) + ' ' + cfg.unit);
    count.className = 'ail-tb-count' + (ok ? ' ok' : '');
    thumbs.replaceChildren.apply(thumbs, cfg.audio
      ? c.imgs.map(function (i, k) { return h('span', { class: 'ail-tr-clip', title: 'Mẩu ' + (k + 1) }, '♪'); })
      : c.imgs.slice(-24).map(function (i) { return h('img', { src: i.uri, alt: '', class: 'ail-tr-th' }); }));
    warn.replaceChildren();
    if (plain(c.name) !== c.name) warn.replaceChildren('Tên lớp nên viết không dấu: ' + plain(c.name) + ' ',
      h('button', { type: 'button', class: 'ail-btn sm', onclick: function () { ops.rename(c, plain(c.name)); nameIn.value = c.name; refresh(); } }, 'Bỏ dấu'));
  }
  refresh();
  return { el: el, refresh: refresh };
}

/* ---- thẻ Xem thử: sau khi train xong, bật camera / micro để thử ngay ---- */
function loadScript(src) {
  return new Promise(function (ok, no) {
    if ([].some.call(document.scripts, function (s) { return s.src === src; })) return ok();
    var s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = function () { no(new Error('Không tải được thư viện ' + src)); };
    document.head.appendChild(s);
  });
}
export function previewCard(cfg) {
  var body = h('div', { class: 'ail-tb-prevbody' });
  var el = panel('eye', 'blue', 'Xem thử', body);
  var run = null;
  function say(t) { body.replaceChildren(h('p', { class: 'meta' }, t)); }
  function stop() { if (run) { run.stop(); run = null; } }
  function reset() { stop(); say('Train mô hình trước, rồi xem thử trực tiếp ở đây.'); }
  function working() { stop(); say('Đang huấn luyện… xong sẽ xem thử được ngay ở đây.'); }
  function ready(job) {
    stop();
    var start = h('button', { type: 'button', class: 'ail-btn pri', onclick: function () { begin(job); } }, ico(cfg.audio ? 'play' : 'camera'), cfg.audio ? 'Bật micro để xem thử' : 'Bật camera để xem thử');
    body.replaceChildren(h('p', { class: 'meta' }, 'Mô hình “' + job.name + '” đã sẵn sàng.'), start);
  }
  function bars(labels) {
    var rows = labels.map(function (l) {
      var fill = h('span', { class: 'ail-tb-fill' }), pct = h('span', { class: 'ail-tb-pct' }, '0%');
      return { l: l, fill: fill, pct: pct, el: h('div', { class: 'ail-tb-bar' }, h('span', { class: 'ail-tb-barname' }, l), h('span', { class: 'ail-tb-track' }, fill), pct) };
    });
    return { rows: rows, set: function (p) {
      rows.forEach(function (r) { var v = Math.round(((p && p[r.l]) || 0) * 100); r.fill.style.width = v + '%'; r.pct.textContent = v + '%'; });
    } };
  }
  function begin(job) {
    say('Đang nạp mô hình…');
    var base = job.url;
    cfg.libs.reduce(function (p, s) { return p.then(function () { return loadScript(s); }); }, Promise.resolve()).then(function () {
      if (cfg.audio) return audio(base, job);
      return camera(base, job);
    }).catch(function (e) {
      var denied = e && (e.name === 'NotAllowedError' || e.name === 'SecurityError');
      body.replaceChildren(h('div', { class: 'err', role: 'alert' }, denied ? 'Bạn chưa cho phép dùng ' + (cfg.audio ? 'micro' : 'camera') + '.' : 'Không xem thử được: ' + ((e && e.message) || e)),
        h('button', { type: 'button', class: 'ail-btn', onclick: function () { ready(job); } }, 'Thử lại'));
    });
  }
  function camera(base, job) {
    var pose = cfg.kind === 'pose';
    return Promise.all([
      pose ? window.tmPose.load(base + 'model.json', base + 'metadata.json') : window.tmImage.load(base + 'model.json', base + 'metadata.json'),
      navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 }, audio: false })
    ]).then(function (r) {
      var model = r[0], stream = r[1], alive = true;
      var video = h('video', { autoplay: true, playsinline: true, class: 'ail-tr-video' }); video.muted = true; video.srcObject = stream;
      var b = bars(model.getClassLabels());
      var stopB = h('button', { type: 'button', class: 'ail-btn', onclick: function () { stop(); ready(job); } }, 'Tắt camera');
      body.replaceChildren(video, h('div', { class: 'ail-tb-bars' }, b.rows.map(function (x) { return x.el; })), stopB);
      video.play();
      run = { stop: function () { alive = false; stream.getTracks().forEach(function (t) { t.stop(); }); } };
      (function loop() {
        if (!alive) return;
        if (!document.body.contains(video)) { stop(); return; }
        var p = video.videoWidth ? (pose ? model.estimatePose(video, true).then(function (o) { return model.predict(o.posenetOutput); }) : model.predict(video, true)) : Promise.resolve(null);
        p.then(function (preds) {
          if (preds) { var m = {}; preds.forEach(function (x) { m[x.className] = x.probability; }); b.set(m); }
          requestAnimationFrame(loop);
        }).catch(function () { setTimeout(loop, 300); });
      })();
    });
  }
  function audio(base, job) {
    var rec = window.speechCommands.create('BROWSER_FFT', undefined, base + 'model.json', base + 'metadata.json');
    return rec.ensureModelLoaded().then(function () {
      var labels = rec.wordLabels(), b = bars(labels);
      var stopB = h('button', { type: 'button', class: 'ail-btn', onclick: function () { stop(); ready(job); } }, 'Tắt micro');
      body.replaceChildren(h('p', { class: 'meta' }, 'Đang nghe… hãy tạo âm thanh của từng lớp.'), h('div', { class: 'ail-tb-bars' }, b.rows.map(function (x) { return x.el; })), stopB);
      return rec.listen(function (res) {
        var m = {}; labels.forEach(function (l, i) { m[l] = res.scores[i]; }); b.set(m);
      }, { includeSpectrogram: false, probabilityThreshold: 0, invokeCallbackOnNoiseAndUnknown: true, overlapFactor: 0.5 }).then(function () {
        run = { stop: function () { try { rec.stopListening(); } catch (e) { /* đã dừng */ } } };
      });
    });
  }
  reset();
  return { el: el, reset: reset, working: working, ready: ready };
}

/* ---- đường nối các thẻ (cột lớp → Huấn luyện → Xem thử) ---- */
export function wires(root) {
  var svg = root.querySelector('.ail-tb-wires');
  if (!svg) { svg = document.createElementNS(NS, 'svg'); svg.setAttribute('class', 'ail-tb-wires'); svg.setAttribute('aria-hidden', 'true'); root.insertBefore(svg, root.firstChild); }
  function draw() {
    var r = root.getBoundingClientRect(), train = root.querySelector('.ail-tb-train'), prev = root.querySelector('.ail-tb-preview');
    if (!train || !prev || r.width < 900) { svg.replaceChildren(); return; }
    var t = train.getBoundingClientRect(), p = prev.getBoundingClientRect(), y2 = t.top - r.top + 36;
    svg.setAttribute('width', r.width); svg.setAttribute('height', r.height); svg.setAttribute('viewBox', '0 0 ' + r.width + ' ' + r.height);
    var d = [];
    [].forEach.call(root.querySelectorAll('.ail-tb-class'), function (c) {
      var b = c.getBoundingClientRect(), x1 = b.right - r.left, y1 = b.top - r.top + b.height / 2, x2 = t.left - r.left, mid = (x1 + x2) / 2;
      d.push('M' + x1 + ' ' + y1 + ' C' + mid + ' ' + y1 + ' ' + mid + ' ' + y2 + ' ' + x2 + ' ' + y2);
    });
    d.push('M' + (t.right - r.left) + ' ' + y2 + ' L' + (p.left - r.left) + ' ' + y2);
    svg.replaceChildren();
    d.forEach(function (s) { var pa = document.createElementNS(NS, 'path'); pa.setAttribute('d', s); svg.appendChild(pa); });
  }
  if (root.__ro) root.__ro.disconnect();
  if (window.ResizeObserver) { root.__ro = new ResizeObserver(draw); root.__ro.observe(root); }
  draw();
  return draw;
}
