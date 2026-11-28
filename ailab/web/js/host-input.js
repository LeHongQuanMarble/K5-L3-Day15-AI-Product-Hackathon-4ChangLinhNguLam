/* host-input.js — cầu nối camera / micro của TRANG CHA tới trình chơi trong iframe (dùng chung cho /play và "Chạy thử").
   Trình chơi KHÔNG tự mở camera/micro (sandbox + CSP). Trang cha mở thiết bị, đọc mô hình rồi gửi postMessage:
   camera.status · camera.image · camera.frame · camera.result · camera.empty · camera.hand.
   Hỗ trợ mô hình: image, pose (Teachable Machine), hands (MediaPipe) bằng camera; audio (Teachable Machine speech-commands) bằng micro. */

var TF = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js';
var LIBS = {
  image: [TF, 'https://cdn.jsdelivr.net/npm/@teachablemachine/image@0.8/dist/teachablemachine-image.min.js'],
  pose: [TF, 'https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js'],
  audio: [TF, 'https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@0.4.0/dist/speech-commands.min.js']
};
var HAND = {
  lib: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs',
  wasm: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm',
  model: 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
};

function loadScript(src) {
  return new Promise(function (ok, bad) {
    if ([].some.call(document.scripts, function (s) { return s.src === src; })) return ok();
    var s = document.createElement('script'); s.src = src; s.onload = ok;
    s.onerror = function () { bad(new Error('Không tải được thư viện: ' + src)); };
    document.head.appendChild(s);
  });
}
export function curlOf(lm, aspect) {
  function d(a, b) { return Math.hypot((a.x - b.x) * aspect, a.y - b.y); }
  var size = d(lm[0], lm[9]) || 1e-6, c = 0;
  [8, 12, 16, 20].forEach(function (t) { c += Math.max(0, Math.min(1, (1.75 - d(lm[t], lm[0]) / size) / 0.6)); });
  return c / 4;
}

/* ---- Giọng nói → chữ (Web Speech API) cho trình chơi gửi {type:'speech',on,lang}; trả lời bằng camera.speech {text,final,available,error}.
   Độc lập với mô hình: trình chơi giọng nói (vd Chim Bay Nói) cần cái này dù ứng dụng có hay không có model. ---- */
export function createSpeech(frame, onSay) {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var rec = null, on = false, lang = 'vi-VN', retry = 0;
  function send(o) { if (frame && frame.contentWindow) frame.contentWindow.postMessage(Object.assign({ type: 'camera.speech' }, o), '*'); }
  function fatal(code) { return code === 'not-allowed' || code === 'service-not-allowed' || code === 'audio-capture' || code === 'language-not-supported'; }
  function stop() {
    on = false; clearTimeout(retry);
    if (rec) { var r = rec; rec = null; r.onend = null; r.onerror = null; r.onresult = null; try { r.abort(); } catch (e) { /* đã dừng */ } }
  }
  function begin() {
    if (!on) return;
    rec = new SR(); rec.lang = lang; rec.continuous = true; rec.interimResults = true; rec.maxAlternatives = 1;
    rec.onresult = function (e) {
      for (var i = e.resultIndex; i < e.results.length; i++) send({ text: e.results[i][0].transcript, final: e.results[i].isFinal, available: true });
    };
    rec.onerror = function (e) {
      if (fatal(e.error)) {
        on = false;
        send({ text: '', final: true, available: false, error: e.error });
        if (onSay) onSay(e.error === 'not-allowed' || e.error === 'service-not-allowed' ? 'Chưa được cấp quyền micro để nghe giọng nói — hãy chọn “Cho phép” rồi thử lại.' : 'Không nghe được giọng nói (' + e.error + ').');
      }
    };
    rec.onend = function () { if (on) retry = setTimeout(begin, 250); }; // trình duyệt tự dừng sau một lúc im lặng → nghe tiếp
    try { rec.start(); } catch (err) { /* đang chạy */ }
  }
  function start(l) {
    if (!SR) { send({ text: '', final: true, available: false, error: 'unsupported' }); if (onSay) onSay('Trình duyệt này không hỗ trợ nhận giọng nói (hãy dùng Chrome hoặc Edge).'); return; }
    stop(); lang = l || lang; on = true; begin();
  }
  return { start: start, stop: stop, message: function (d) { if (d && d.type === 'speech') { if (d.on) start(typeof d.lang === 'string' ? d.lang : null); else stop(); } } };
}

/* ---- vẽ khung xương lên canvas phủ trên video (toạ độ theo pixel của video) ---- */
var POSE_PAIRS = [['leftShoulder', 'rightShoulder'], ['leftShoulder', 'leftElbow'], ['leftElbow', 'leftWrist'], ['rightShoulder', 'rightElbow'], ['rightElbow', 'rightWrist'],
  ['leftShoulder', 'leftHip'], ['rightShoulder', 'rightHip'], ['leftHip', 'rightHip'], ['leftHip', 'leftKnee'], ['leftKnee', 'leftAnkle'], ['rightHip', 'rightKnee'], ['rightKnee', 'rightAnkle'],
  ['nose', 'leftEye'], ['nose', 'rightEye'], ['leftEye', 'leftEar'], ['rightEye', 'rightEar']];
var HAND_PAIRS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
function prep(canvas, video) {
  if (canvas.width !== video.videoWidth) canvas.width = video.videoWidth;
  if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight;
  var g = canvas.getContext('2d'); g.clearRect(0, 0, canvas.width, canvas.height);
  g.lineCap = 'round'; g.lineWidth = Math.max(3, canvas.width / 160);
  return g;
}
export function drawPose(canvas, video, pose, minScore) {
  var g = prep(canvas, video); if (!pose || !pose.keypoints) return;
  var min = minScore == null ? 0.4 : minScore, by = {}, r = Math.max(4, canvas.width / 110);
  pose.keypoints.forEach(function (k) { if (k.score >= min) by[k.part] = k.position; });
  g.strokeStyle = '#22d3ee';
  POSE_PAIRS.forEach(function (p) { var a = by[p[0]], b = by[p[1]]; if (a && b) { g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); } });
  g.fillStyle = '#facc15';
  Object.keys(by).forEach(function (n) { g.beginPath(); g.arc(by[n].x, by[n].y, r, 0, 6.2832); g.fill(); });
}
export function drawHands(canvas, video, hands) { // hands: [[{x,y} chuẩn hoá 0..1 ×21]]
  var g = prep(canvas, video), W = canvas.width, H = canvas.height, r = Math.max(3, W / 150);
  (hands || []).forEach(function (lm) {
    g.strokeStyle = '#22d3ee';
    HAND_PAIRS.forEach(function (p) { var a = lm[p[0]], b = lm[p[1]]; g.beginPath(); g.moveTo(a.x * W, a.y * H); g.lineTo(b.x * W, b.y * H); g.stroke(); });
    g.fillStyle = '#facc15';
    lm.forEach(function (q) { g.beginPath(); g.arc(q.x * W, q.y * H, r, 0, 6.2832); g.fill(); });
  });
}

/* Bộ đọc bàn tay MediaPipe dùng chung (nạp một lần). */
var sharedLandmarker = null;
export function loadHandLandmarker() {
  if (sharedLandmarker) return Promise.resolve(sharedLandmarker);
  return import(HAND.lib).then(function (mp) {
    return mp.FilesetResolver.forVisionTasks(HAND.wasm).then(function (files) {
      return mp.HandLandmarker.createFromOptions(files, { baseOptions: { modelAssetPath: HAND.model }, runningMode: 'VIDEO', numHands: 2 });
    });
  }).then(function (l) { sharedLandmarker = l; return l; });
}

/* o = { frame, model:{kind,url}, mapping:{đầuVào:lớp}, sure, holdMs, onSay(text), onRunning(bool) } */
export function createHostInput(o) {
  var kind = o.model.kind, isAudio = kind === 'audio';
  var sure = o.sure == null ? 0.8 : o.sure, holdMs = o.holdMs == null ? 800 : o.holdMs;
  var say = o.onSay || function () {}, onRunning = o.onRunning || function () {};
  var rev = {}; Object.keys(o.mapping || {}).forEach(function (k) { rev[o.mapping[k]] = k; });
  var running = false, want = false, handsAsked = false, landmarker = null, handNow = { present: false, fist: false };
  var video = null, stream = null, tm = null, rec = null, loopId = 0, lastFrame = 0, lastHand = 0, lastPredict = 0, busy = false;
  var actx = null, analyser = null, vizStream = null, vizId = 0, lastViz = 0, vizData = null, vizCanvas = null;
  var cand = null, since = 0, emitted = false, canvas = document.createElement('canvas');
  var thing = isAudio ? 'micro' : 'camera';
  var hint = o.fallbackHint || '';

  function toFrame(m, transfer) { if (o.frame && o.frame.contentWindow) o.frame.contentWindow.postMessage(m, '*', transfer || []); }
  function st(state) { toFrame({ type: 'camera.status', state: state, source: 'camera' }); }
  function handsFail() { toFrame({ type: 'camera.hand', hands: [], available: false }); }
  function loadHands() {
    if (landmarker) return Promise.resolve();
    return import(HAND.lib).then(function (mp) {
      return mp.FilesetResolver.forVisionTasks(HAND.wasm).then(function (files) {
        return mp.HandLandmarker.createFromOptions(files, { baseOptions: { modelAssetPath: HAND.model }, runningMode: 'VIDEO', numHands: 2 });
      });
    }).then(function (l) { landmarker = l; });
  }
  function readHands(now) {
    var r;
    try { r = landmarker.detectForVideo(video, now); } catch (e) { return; }
    var hands = (r && r.landmarks || []).map(function (lm) { return lm.map(function (p) { return { x: 1 - p.x, y: p.y, z: p.z || 0 }; }); });
    if (handsAsked) toFrame({ type: 'camera.hand', hands: hands, available: true });
    if (!hands.length) { handNow = { present: false, fist: false }; return; }
    var curl = curlOf(hands[0], video.videoWidth / video.videoHeight);
    handNow = { present: true, fist: handNow.present ? (handNow.fist ? curl > 0.4 : curl > 0.6) : curl > 0.6 };
  }
  /* mọi loại mô hình đều ra cùng dạng [{className, probability}] rồi qua đây */
  function decide(preds) {
    var top = preds.reduce(function (a, b) { return b.probability > a.probability ? b : a; });
    var scores = {}; preds.forEach(function (x) { if (rev[x.className]) scores[rev[x.className]] = x.probability; });
    toFrame({ type: 'camera.frame', scores: scores });
    var input = rev[top.className];
    var key = input && top.probability >= sure ? input + '|' + top.className : null;
    var t = performance.now();
    if (key !== cand) { cand = key; since = t; emitted = false; if (!key) toFrame({ type: 'camera.empty' }); }
    else if (key && !emitted && t - since >= holdMs) {
      emitted = true; toFrame({ type: 'camera.result', input: input, label: top.className, confidence: top.probability });
    }
  }
  function predictCamera() {
    var p;
    if (kind === 'hands') p = Promise.resolve([{ className: 'fist', probability: handNow.present && handNow.fist ? 1 : 0 }, { className: 'open', probability: handNow.present && !handNow.fist ? 1 : 0 }, { className: 'none', probability: handNow.present ? 0 : 1 }]);
    else if (kind === 'pose') p = tm.estimatePose(video).then(function (r) { return tm.predict(r.posenetOutput); });
    else p = tm.predict(video);
    return p.then(decide);
  }
  function loop() {
    if (!running) return;
    loopId = requestAnimationFrame(loop);
    var now = performance.now();
    if (want && now - lastFrame > 66 && video.videoWidth) {
      lastFrame = now;
      canvas.width = video.videoWidth; canvas.height = video.videoHeight;
      var cx = canvas.getContext('2d'); cx.save(); cx.scale(-1, 1); cx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height); cx.restore();
      createImageBitmap(canvas, { resizeWidth: Math.min(640, canvas.width) }).then(function (b) { toFrame({ type: 'camera.image', image: b }, [b]); }).catch(function () {});
    }
    if (landmarker && video.videoWidth && now - lastHand > 66) { lastHand = now; readHands(now); }
    if (!busy && now - lastPredict > 120) { lastPredict = now; busy = true; predictCamera().then(function () { busy = false; }, function () { busy = false; }); }
  }
  /* Micro: vẽ phổ tần số (analyser) thành ảnh gửi vào ô [data-jl-camera] của trình chơi, như khung camera. */
  function startViz() {
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
      if (!running) { s.getTracks().forEach(function (t) { t.stop(); }); return; }
      vizStream = s;
      var AC = window.AudioContext || window.webkitAudioContext; actx = new AC(); if (actx.resume) actx.resume();
      var src = actx.createMediaStreamSource(s); analyser = actx.createAnalyser();
      analyser.fftSize = 1024; analyser.smoothingTimeConstant = 0.6; src.connect(analyser); // không nối ra loa
      vizData = new Uint8Array(analyser.frequencyBinCount);
      vizCanvas = document.createElement('canvas'); vizCanvas.width = 480; vizCanvas.height = 300;
      vizLoop();
    }).catch(function () { /* không có phổ thì vẫn nhận diện được */ });
  }
  function vizLoop() {
    if (!running || !analyser) return;
    vizId = requestAnimationFrame(vizLoop);
    var now = performance.now();
    if (!want || now - lastViz < 66) return;
    lastViz = now;
    analyser.getByteFrequencyData(vizData);
    var W = vizCanvas.width, H = vizCanvas.height, g = vizCanvas.getContext('2d'), hz = actx.sampleRate / analyser.fftSize;
    var maxHz = 8000, n = Math.min(vizData.length, Math.floor(maxHz / hz)), bw = W / n, padB = 24;
    g.fillStyle = '#0b1020'; g.fillRect(0, 0, W, H);
    for (var i = 0; i < n; i++) {
      var v = vizData[i] / 255, bh = v * (H - padB - 8);
      g.fillStyle = 'hsl(' + Math.round(200 - v * 170) + ',90%,' + Math.round(45 + v * 20) + '%)';
      g.fillRect(i * bw, H - padB - bh, Math.max(1, bw - 1), bh);
    }
    g.fillStyle = '#9aa4c7'; g.font = '14px sans-serif'; g.textBaseline = 'bottom';
    [0, 2000, 4000, 6000, 8000].forEach(function (f, k) {
      var x = Math.min(W - 40, (f / hz) * bw); g.fillText(f === 0 ? '0 Hz' : (f / 1000) + ' kHz', k === 0 ? 4 : x - (k === 4 ? 36 : 14), H - 4);
    });
    createImageBitmap(vizCanvas).then(function (b) { toFrame({ type: 'camera.image', image: b }, [b]); }).catch(function () {});
  }
  function stopViz() {
    cancelAnimationFrame(vizId); analyser = null;
    if (vizStream) vizStream.getTracks().forEach(function (t) { t.stop(); }); vizStream = null;
    if (actx) { try { actx.close(); } catch (e) { /* đã đóng */ } actx = null; }
  }
  function fail(err) {
    var name = err && err.name;
    var denied = name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError';
    var none = name === 'NotFoundError' || name === 'DevicesNotFoundError';
    var used = name === 'NotReadableError' || name === 'TrackStartError';
    st(denied ? 'denied' : none ? 'no-camera' : used ? 'busy' : 'model-failed');
    say((denied ? 'Bạn chưa cho phép trang này dùng ' + thing + ' — hãy chọn “Cho phép” khi trình duyệt hỏi (biểu tượng ổ khoá trên thanh địa chỉ).'
      : none ? 'Không tìm thấy ' + thing + ' trên máy này.'
      : used ? thing + ' đang được ứng dụng khác sử dụng — đóng ứng dụng đó rồi thử lại.'
      : 'Không bật được ' + thing + ' hoặc nạp mô hình: ' + (err && err.message || err)) + hint);
    stop(true);
  }
  function start() {
    if (running) return Promise.resolve();
    onRunning(null); say('Đang bật ' + thing + ' và nạp mô hình…'); st('loading');
    if (kind !== 'hands' && !LIBS[kind]) { st('model-failed'); say('Mô hình ' + kind + ' chưa chạy được ở bản này.' + hint); onRunning(false); return Promise.resolve(); }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { st('no-camera'); say('Trình duyệt chỉ cho dùng ' + thing + ' khi mở bằng https hoặc localhost.' + hint); onRunning(false); return Promise.resolve(); }
    cand = null; emitted = false;
    var libs = LIBS[kind] || [];
    var loaded = libs.reduce(function (p, src) { return p.then(function () { return loadScript(src); }); }, Promise.resolve());
    if (isAudio) {
      return loaded.then(function () {
        rec = window.speechCommands.create('BROWSER_FFT', undefined, o.model.url + 'model.json', o.model.url + 'metadata.json');
        return rec.ensureModelLoaded();
      }).then(function () {
        var labels = rec.wordLabels();
        return rec.listen(function (res) {
          decide(labels.map(function (l, i) { return { className: l, probability: res.scores[i] }; }));
        }, { includeSpectrogram: false, probabilityThreshold: 0, invokeCallbackOnNoiseAndUnknown: true, overlapFactor: 0.75 });
      }).then(function () { running = true; say('Đang nghe — hãy tạo âm thanh để chọn đáp án.'); st('ready'); onRunning(true); startViz(); }).catch(fail);
    }
    return navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false }).then(function (s) {
      stream = s;
      video = document.createElement('video'); video.playsInline = true; video.muted = true; video.srcObject = s;
      return video.play();
    }).then(function () { return loaded; }).then(function () {
      if (kind === 'hands') return loadHands().then(function () { return null; });
      return kind === 'image' ? window.tmImage.load(o.model.url + 'model.json', o.model.url + 'metadata.json') : window.tmPose.load(o.model.url + 'model.json', o.model.url + 'metadata.json');
    }).then(function (m) {
      tm = m; running = true;
      if (handsAsked && kind !== 'hands') loadHands().catch(handsFail);
      say('Đang chạy'); st('ready'); onRunning(true); loop();
    }).catch(fail);
  }
  function stop(keepStatus) {
    running = false; cancelAnimationFrame(loopId); stopViz();
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); }); stream = null;
    if (rec) { try { rec.stopListening(); } catch (e) { /* đã dừng */ } rec = null; }
    onRunning(false);
    if (!keepStatus) { st('off'); say(thing[0].toUpperCase() + thing.slice(1) + ' đã tắt — đang chơi bằng chuột.'); }
  }
  /* tin nhắn từ trình chơi: camera.want / hands */
  function message(d) {
    if (!d) return;
    if (d.type === 'camera.want') want = !!d.on;
    if (d.type === 'hands') {
      handsAsked = d.on === true;
      if (handsAsked && running && !landmarker && !isAudio) loadHands().catch(handsFail);
      else if (handsAsked && (!running || isAudio)) handsFail();
    }
  }
  return { start: start, stop: stop, message: message, isRunning: function () { return running; },
    status: function () { st(running ? 'ready' : 'off'); }, thing: thing };
}
