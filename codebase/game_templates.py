"""Hybrid GENERATE — Verified HTML Game Templates (P0).

Cung cấp 2 khung trò chơi HTML chuẩn, chạy hoàn toàn cục bộ trong iframe sandbox (0 cờ an toàn):
1. `matching_cards`: Ghép cặp thẻ (từ vựng / khái niệm / mốc sự kiện) — đọc động `questions` qua `camera.init`,
   chấm điểm, hiển thị đúng/sai, kết thúc gửi `finish`, nút Chơi lại (Reset), 100% Mouse Fallback + bàn phím.
2. `true_false`: Đúng/Sai tốc độ hoặc trắc nghiệm nhanh — đọc động `questions` qua `camera.init`,
   chấm điểm, chuyển câu, kết thúc gửi `finish`, nút Chơi lại (Reset), 100% Mouse Fallback + bàn phím.

Nguyên tắc:
- Không hardcode kiến thức bài học; mọi câu hỏi đi từ `exam.content` (đã qua `parse_questions`).
- Escape toàn bộ dữ liệu bằng `textContent` và thoát `</` trong JSON manifest (không XSS).
- Manifest sạch (`questions: "exam"`, KHÔNG khai trùng `content.kind: "texts"`).
"""
import html as _html
import json
import re

_MATCHING_RE = re.compile(r"\b(?:ghep cap|ghep the|noi cap|noi the|noi cot|matching|match card|cap the|lat the)\b", re.I)
_TRUE_FALSE_RE = re.compile(r"\b(?:dung\s*/?\s*sai|true\s*/?\s*false|flashcard|the ghi nho)\b", re.I)


def _fold(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", (text or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def detect_template(user_msg: str, game_idea: str = "") -> str | None:
    """Nhận diện xem yêu cầu có khớp một khung đã kiểm chứng không. Trả tên template hoặc None (free-form)."""
    combined = _fold((user_msg or "") + " " + (game_idea or ""))
    if _MATCHING_RE.search(combined):
        return "matching_cards"
    if _TRUE_FALSE_RE.search(combined):
        return "true_false"
    return None


def _safe_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _safe_title(text: str, fallback: str) -> str:
    clean = (text or "").strip()[:80] or fallback
    return _html.escape(clean, quote=True)


def render_matching_cards(name: str, description: str, demo_questions: list) -> str:
    """Dựng HTML khung Ghép cặp thẻ từ manifest + demo_questions động (0 cờ an toàn, 100% textContent)."""
    title = (name or "Ghép cặp thẻ").strip()[:80] or "Ghép cặp thẻ"
    desc = (description or "Trò chơi ghép cặp thẻ tương tác chơi bằng chuột/chạm/bàn phím.").strip()[:200]
    manifest = {
        "name": title,
        "description": desc,
        "questions": "exam",
        "demo": {"questions": demo_questions[:6] if isinstance(demo_questions, list) else []},
    }
    return """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE_ESC__</title>
<script type="application/json" id="jl-camera">
__MANIFEST_JSON__
</script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#f4f6fb;color:#1b2430;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:16px}
  .wrap{width:100%;max-width:760px;background:#fff;border-radius:16px;padding:20px;box-shadow:0 4px 20px rgba(15,23,42,.08)}
  .top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}
  .title{font-size:20px;font-weight:700;margin:0}
  .stats{display:flex;gap:8px;font-size:14px;font-weight:600}
  .pill{background:#eef2ff;color:#3730a3;padding:6px 12px;border-radius:999px}
  .status{min-height:24px;font-size:14px;margin:0 0 12px;color:#475569}
  .status.ok{color:#15803d;font-weight:600}
  .status.bad{color:#b91c1c;font-weight:600}
  .board{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .col{display:flex;flex-direction:column;gap:10px}
  .col h3{margin:0 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#64748b}
  .card{width:100%;text-align:left;padding:12px 14px;border:2px solid #cbd5e1;border-radius:12px;background:#fff;color:#0f172a;font-size:15px;cursor:pointer;transition:border-color .15s,background .15s,transform .1s}
  .card:hover:not(:disabled){border-color:#6366f1;background:#f8faff}
  .card.sel{border-color:#4f46e5;background:#eef2ff;font-weight:600}
  .card.done{border-color:#22c55e;background:#dcfce7;color:#14532d;cursor:default}
  .card.wrong{border-color:#ef4444;background:#fee2e2;color:#991b1b}
  .foot{display:flex;justify-content:space-between;align-items:center;margin-top:16px;gap:10px;flex-wrap:wrap}
  .btn{padding:10px 18px;border:0;border-radius:10px;background:#4f46e5;color:#fff;font-size:14px;font-weight:600;cursor:pointer}
  .btn:hover{background:#4338ca}
  .done-box{margin-top:14px;padding:14px;border-radius:12px;background:#ecfdf5;border:1px solid #86efac;color:#14532d;display:none}
  .done-box.show{display:block}
  @media (max-width:540px){.board{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1 class="title" id="game-title">__TITLE_ESC__</h1>
    <div class="stats">
      <span class="pill" id="score-pill">Đúng: 0/0</span>
      <span class="pill" id="tries-pill">Lượt: 0</span>
    </div>
  </div>
  <p class="status" id="status" role="status" aria-live="polite">Chọn 1 thẻ bên trái và 1 thẻ tương ứng bên phải.</p>
  <div class="board">
    <div class="col"><h3>Câu hỏi / Khái niệm</h3><div id="left-col" class="col"></div></div>
    <div class="col"><h3>Đáp án tương ứng</h3><div id="right-col" class="col"></div></div>
  </div>
  <div class="done-box" id="done-box"></div>
  <div class="foot">
    <span style="font-size:13px;color:#64748b">Hỗ trợ chuột, cảm ứng và bàn phím (Mouse Fallback).</span>
    <button type="button" class="btn" id="reset-btn">Chơi lại</button>
  </div>
</div>
<script>
(function(){
  var pairs = [], matched = {}, selLeft = null, selRight = null, tries = 0, score = 0, finished = false;
  var leftCol = document.getElementById('left-col');
  var rightCol = document.getElementById('right-col');
  var statusEl = document.getElementById('status');
  var scorePill = document.getElementById('score-pill');
  var triesPill = document.getElementById('tries-pill');
  var doneBox = document.getElementById('done-box');

  function extractPairs(qs){
    var out = [];
    (qs || []).forEach(function(q, idx){
      if (!q || !q.text) return;
      var ansText = '';
      var ch = q.choices || [];
      for (var i = 0; i < ch.length; i++){
        if (ch[i] && ch[i].key === q.answer){ ansText = ch[i].text || ch[i].key; break; }
      }
      if (!ansText && q.answer) ansText = String(q.answer);
      if (ansText) out.push({ id: String(q.id || ('p' + idx)), left: String(q.text), right: String(ansText) });
    });
    return out;
  }

  function shuffle(arr){
    var copy = arr.slice();
    for (var i = copy.length - 1; i > 0; i--){
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = copy[i]; copy[i] = copy[j]; copy[j] = tmp;
    }
    return copy;
  }

  function setStatus(msg, cls){
    statusEl.textContent = msg;
    statusEl.className = 'status' + (cls ? ' ' + cls : '');
  }

  function updateStats(){
    scorePill.textContent = 'Đúng: ' + score + '/' + pairs.length;
    triesPill.textContent = 'Lượt: ' + tries;
  }

  function checkPair(){
    if (!selLeft || !selRight) return;
    tries++;
    var lId = selLeft.dataset.id, rId = selRight.dataset.id;
    var lb = selLeft, rb = selRight;
    selLeft = null; selRight = null;
    if (lId === rId){
      matched[lId] = true;
      score++;
      lb.className = 'card done'; lb.disabled = true;
      rb.className = 'card done'; rb.disabled = true;
      setStatus('Chính xác! Bạn đã ghép đúng 1 cặp.', 'ok');
      updateStats();
      if (score === pairs.length && pairs.length > 0 && !finished){
        finished = true;
        doneBox.textContent = 'Hoàn thành! Bạn đã ghép đúng tất cả ' + score + '/' + pairs.length + ' cặp sau ' + tries + ' lượt.';
        doneBox.className = 'done-box show';
        parent.postMessage({ type: 'finish', score: score, total: pairs.length }, '*');
      }
    } else {
      lb.className = 'card wrong'; rb.className = 'card wrong';
      setStatus('Chưa khớp, hãy thử lại nhé!', 'bad');
      updateStats();
      setTimeout(function(){
        if (!matched[lId]) lb.className = 'card';
        if (!matched[rId]) rb.className = 'card';
      }, 650);
    }
  }

  function renderBoard(){
    matched = {}; selLeft = null; selRight = null; tries = 0; score = 0; finished = false;
    doneBox.className = 'done-box'; doneBox.textContent = '';
    leftCol.innerHTML = ''; rightCol.innerHTML = '';
    if (!pairs.length){
      setStatus('Chưa có dữ liệu câu hỏi để ghép cặp.', 'bad');
      updateStats();
      return;
    }
    pairs.forEach(function(p){
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'card'; b.dataset.id = p.id; b.textContent = p.left;
      b.addEventListener('click', function(){
        if (matched[p.id]) return;
        if (selLeft) selLeft.className = 'card';
        selLeft = b; b.className = 'card sel';
        checkPair();
      });
      leftCol.appendChild(b);
    });
    shuffle(pairs).forEach(function(p){
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'card'; b.dataset.id = p.id; b.textContent = p.right;
      b.addEventListener('click', function(){
        if (matched[p.id]) return;
        if (selRight) selRight.className = 'card';
        selRight = b; b.className = 'card sel';
        checkPair();
      });
      rightCol.appendChild(b);
    });
    setStatus('Chọn 1 thẻ bên trái và 1 thẻ tương ứng bên phải.', '');
    updateStats();
  }

  document.getElementById('reset-btn').addEventListener('click', renderBoard);

  window.addEventListener('message', function(e){
    var d = e.data;
    if (!d || e.source !== parent) return;
    if (d.type === 'camera.init'){
      pairs = extractPairs(d.questions);
      renderBoard();
    }
  });

  try {
    var man = JSON.parse(document.getElementById('jl-camera').textContent || '{}');
    if (man.demo && man.demo.questions) { pairs = extractPairs(man.demo.questions); renderBoard(); }
  } catch (e) {}

  parent.postMessage({ type: 'ready' }, '*');
})();
</script>
</body>
</html>""".replace("__TITLE_ESC__", _safe_title(title, "Ghép cặp thẻ")).replace("__MANIFEST_JSON__", _safe_json(manifest))


def render_true_false(name: str, description: str, demo_questions: list) -> str:
    """Dựng HTML khung Đúng/Sai tốc độ & Trắc nghiệm nhanh (0 cờ an toàn, 100% textContent)."""
    title = (name or "Thử thách Đúng / Sai").strip()[:80] or "Thử thách Đúng / Sai"
    desc = (description or "Trò chơi trả lời nhanh Đúng/Sai hoặc trắc nghiệm chơi bằng chuột/bàn phím.").strip()[:200]
    manifest = {
        "name": title,
        "description": desc,
        "questions": "exam",
        "demo": {"questions": demo_questions[:6] if isinstance(demo_questions, list) else []},
    }
    return """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE_ESC__</title>
<script type="application/json" id="jl-camera">
__MANIFEST_JSON__
</script>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#f4f6fb;color:#1b2430;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:16px}
  .wrap{width:100%;max-width:680px;background:#fff;border-radius:16px;padding:22px;box-shadow:0 4px 20px rgba(15,23,42,.08)}
  .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
  .title{font-size:20px;font-weight:700;margin:0}
  .pill{background:#eef2ff;color:#3730a3;padding:6px 12px;border-radius:999px;font-size:14px;font-weight:600}
  .qbox{padding:18px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;font-size:18px;font-weight:600;margin-bottom:14px;min-height:76px;display:flex;align-items:center}
  .opts{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .opt{padding:14px 16px;border:2px solid #cbd5e1;border-radius:12px;background:#fff;color:#0f172a;font-size:15px;font-weight:600;cursor:pointer;text-align:left}
  .opt:hover:not(:disabled){border-color:#4f46e5;background:#eef2ff}
  .opt.ok{border-color:#22c55e;background:#dcfce7;color:#14532d}
  .opt.bad{border-color:#ef4444;background:#fee2e2;color:#991b1b}
  .feedback{min-height:24px;margin:12px 0;font-size:15px;font-weight:600}
  .feedback.ok{color:#15803d}
  .feedback.bad{color:#b91c1c}
  .foot{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap}
  .btn{padding:10px 18px;border:0;border-radius:10px;background:#4f46e5;color:#fff;font-size:14px;font-weight:600;cursor:pointer}
  .btn:hover{background:#4338ca}
  .btn.sec{background:#e2e8f0;color:#1e293b}
  @media (max-width:500px){.opts{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1 class="title">__TITLE_ESC__</h1>
    <div>
      <span class="pill" id="prog-pill">Câu 0/0</span>
      <span class="pill" id="score-pill">Điểm: 0</span>
    </div>
  </div>
  <div class="qbox" id="qtext">Đang nạp câu hỏi...</div>
  <div class="opts" id="opts"></div>
  <div class="feedback" id="feedback" role="status" aria-live="polite"></div>
  <div class="foot">
    <button type="button" class="btn sec" id="reset-btn">Chơi lại</button>
    <button type="button" class="btn" id="next-btn" style="display:none">Câu tiếp theo</button>
  </div>
</div>
<script>
(function(){
  var qs = [], idx = 0, score = 0, locked = false;
  var qtext = document.getElementById('qtext');
  var optsEl = document.getElementById('opts');
  var fbEl = document.getElementById('feedback');
  var progPill = document.getElementById('prog-pill');
  var scorePill = document.getElementById('score-pill');
  var nextBtn = document.getElementById('next-btn');

  function updateHeader(){
    var total = qs.length;
    progPill.textContent = total ? ('Câu ' + Math.min(idx + 1, total) + '/' + total) : 'Câu 0/0';
    scorePill.textContent = 'Điểm: ' + score + '/' + total;
  }

  function showQuestion(){
    locked = false;
    fbEl.textContent = ''; fbEl.className = 'feedback';
    nextBtn.style.display = 'none';
    optsEl.innerHTML = '';
    updateHeader();
    if (!qs.length){
      qtext.textContent = 'Chưa có câu hỏi.';
      return;
    }
    if (idx >= qs.length){
      qtext.textContent = 'Hoàn thành! Tổng điểm của bạn: ' + score + '/' + qs.length + '.';
      parent.postMessage({ type: 'finish', score: score, total: qs.length }, '*');
      return;
    }
    var q = qs[idx];
    qtext.textContent = q.text || '';
    (q.choices || []).forEach(function(c){
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'opt'; b.dataset.key = c.key;
      b.textContent = (q.type === 'truefalse' ? '' : (c.key + '. ')) + (c.text || c.key);
      b.addEventListener('click', function(){ answer(c.key); });
      optsEl.appendChild(b);
    });
  }

  function answer(key){
    if (locked || idx >= qs.length) return;
    locked = true;
    var q = qs[idx];
    var ok = key === q.answer;
    if (ok) score++;
    var btns = optsEl.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++){
      btns[i].disabled = true;
      if (btns[i].dataset.key === q.answer) btns[i].className = 'opt ok';
      else if (btns[i].dataset.key === key && !ok) btns[i].className = 'opt bad';
    }
    fbEl.textContent = ok ? 'Chính xác!' : ('Chưa đúng. Đáp án đúng là: ' + q.answer);
    fbEl.className = 'feedback ' + (ok ? 'ok' : 'bad');
    updateHeader();
    nextBtn.textContent = (idx + 1 < qs.length) ? 'Câu tiếp theo' : 'Xem kết quả';
    nextBtn.style.display = 'inline-block';
  }

  nextBtn.addEventListener('click', function(){ idx++; showQuestion(); });
  document.getElementById('reset-btn').addEventListener('click', function(){ idx = 0; score = 0; showQuestion(); });

  window.addEventListener('message', function(e){
    var d = e.data;
    if (!d || e.source !== parent) return;
    if (d.type === 'camera.init'){
      qs = Array.isArray(d.questions) ? d.questions : [];
      idx = 0; score = 0;
      showQuestion();
    }
  });

  try {
    var man = JSON.parse(document.getElementById('jl-camera').textContent || '{}');
    if (man.demo && Array.isArray(man.demo.questions)) { qs = man.demo.questions; showQuestion(); }
  } catch (e) {}

  parent.postMessage({ type: 'ready' }, '*');
})();
</script>
</body>
</html>""".replace("__TITLE_ESC__", _safe_title(title, "Thử thách Đúng / Sai")).replace("__MANIFEST_JSON__", _safe_json(manifest))


def render_template(kind: str, name: str, description: str, demo_questions: list) -> str:
    if kind == "matching_cards":
        return render_matching_cards(name, description, demo_questions)
    if kind == "true_false":
        return render_true_false(name, description, demo_questions)
    raise ValueError("Unsupported template kind: %s" % kind)
