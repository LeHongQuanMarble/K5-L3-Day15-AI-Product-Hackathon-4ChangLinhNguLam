"""Deterministic Runtime Wrapper & Player Assembler for Spec-driven Model-aware GENERATE.

Tách bạch trách nhiệm để tăng độ ổn định gameplay do AI sinh:
- **Deterministic Runtime Wrapper (hệ thống kiểm soát 100%):**
  * Dựng khối `<script type="application/json" id="jl-camera">` chính xác theo `GameSpec` (0 xung đột manifest).
  * Cung cấp đối tượng `window.JLRuntime` bên trong iframe sandbox:
    - Bắt tay chuẩn `ready` + tự gửi `{type:'hands', on:true}` khi `uses_hand_landmarks=True`.
    - Lắng nghe `camera.init`, `camera.hand` (chuẩn hóa `indexTip = lm[8]`, `palm = lm[9]`), `camera.result`
      (kèm debounce chống chọn lặp), `camera.frame`.
    - Cung cấp HUD chuẩn (Tên game, Điểm, Tiến độ, nút Chơi lại/Reset, `<div data-jl-camera>` khi có Model)
      và bẫy lỗi `window.onerror` thân thiện.
- **AI-generated Gameplay (AI tập trung vào cơ chế & hình ảnh mới):**
  * AI chỉ cần sinh đoạn `<style>` + HTML sân chơi + `<script>` dùng `JLRuntime.onInit`, `JLRuntime.onHand`,
    `JLRuntime.onAction`, `JLRuntime.setScore`, `JLRuntime.finish` (kèm chuột/chạm/bàn phím).
  * `assemble_player(spec, gameplay_snippet, demo_questions)` lắp thành file HTML tự đủ, 0 cờ an toàn, qua L1–L4.
"""
import html as _html
import json
import re

_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
_SCRIPT_RE = re.compile(r"<script\b(?![^>]*application/json)[^>]*>(.*?)</script>", re.S | re.I)
_BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.S | re.I)


def _safe_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_manifest_from_spec(spec: dict, demo_questions: list | None = None) -> dict:
    """Dựng manifest `jl-camera` tất định từ GameSpec (đảm bảo 100% khớp kinds/inputs/questions)."""
    title = (spec.get("title") or "Trò chơi tương tác mới").strip()[:60] or "Trò chơi tương tác mới"
    desc = (spec.get("game_mechanic") or "Trò chơi tương tác hỗ trợ chuột và mô hình AI.").strip()[:200]
    mc = spec.get("model_capabilities")
    inter = spec.get("interaction_requirements") or {}
    man = {"name": title, "description": desc, "questions": "exam"}
    if isinstance(mc, dict) and mc.get("kind") and inter.get("inputs"):
        man["kinds"] = [mc["kind"]]
        man["inputs"] = inter["inputs"]
    if isinstance(demo_questions, list) and demo_questions:
        man["demo"] = {"questions": demo_questions[:6]}
    return man


def extract_gameplay_parts(raw_snippet: str) -> tuple[str, str, str]:
    """Tách (css, markup, js) từ đoạn gameplay AI sinh (hỗ trợ cả mảnh HTML lẫn file HTML đầy đủ)."""
    text = (raw_snippet or "").strip()
    css_parts = [m.group(1).strip() for m in _STYLE_RE.finditer(text)]
    js_parts = [m.group(1).strip() for m in _SCRIPT_RE.finditer(text)]
    body_m = _BODY_RE.search(text)
    markup = body_m.group(1) if body_m else text
    markup = _STYLE_RE.sub("", markup)
    markup = _SCRIPT_RE.sub("", markup)
    markup = re.sub(r"<script\b[^>]*application/json[^>]*>.*?</script>", "", markup, flags=re.S | re.I)
    markup = re.sub(r"<!doctype[^>]*>|</?(?:html|head|meta|title|body)[^>]*>", "", markup, flags=re.I).strip()
    return "\n".join(css_parts), markup, "\n".join(js_parts)


def assemble_player(spec: dict, gameplay_snippet: str, demo_questions: list | None = None) -> str:
    """Lắp Deterministic Runtime Wrapper + AI-generated Gameplay thành 1 file HTML tự đủ (0 cờ an toàn)."""
    man = build_manifest_from_spec(spec, demo_questions=demo_questions)
    title_esc = _html.escape(man["name"], quote=True)
    mc = spec.get("model_capabilities")
    has_model = isinstance(mc, dict) and bool(mc.get("kind"))
    uses_hands = bool(has_model and mc.get("uses_hand_landmarks"))
    css, markup, js = extract_gameplay_parts(gameplay_snippet)
    cam_box = '<div class="jl-cam-pip" data-jl-camera aria-label="Khung camera"></div>' if has_model else ""
    hand_cursor = '<div id="jl-hand-cursor" class="jl-hand-cursor" aria-hidden="true"></div>' if uses_hands else ""

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
  body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#f8fafc;min-height:100vh;display:flex;flex-direction:column}
  .jl-hud{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 16px;background:#1e293b;border-bottom:1px solid rgba(255,255,255,.1)}
  .jl-hud-title{font-size:16px;font-weight:700;margin:0}
  .jl-hud-stats{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .jl-pill{padding:5px 11px;border-radius:999px;background:rgba(99,102,241,.22);color:#e0e7ff;font-size:13px;font-weight:600}
  .jl-btn{padding:7px 14px;border:0;border-radius:9px;background:#4f46e5;color:#fff;font-size:13px;font-weight:600;cursor:pointer}
  .jl-btn:hover{background:#4338ca}
  .jl-stage{position:relative;flex:1;min-height:420px;padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden}
  .jl-cam-pip{position:fixed;right:12px;bottom:12px;width:168px;height:126px;border-radius:12px;overflow:hidden;background:#020617;border:2px solid rgba(255,255,255,.18);z-index:20}
  .jl-cam-pip canvas{width:100%;height:100%;object-fit:cover;display:block}
  .jl-hand-cursor{position:fixed;width:24px;height:24px;border-radius:50%;border:3px solid #38bdf8;background:rgba(56,189,248,.28);pointer-events:none;transform:translate(-50%,-50%);display:none;z-index:30}
  .jl-err{display:none;margin:12px;padding:12px 16px;border-radius:10px;background:#7f1d1d;color:#fecaca;font-size:14px}
  .jl-err.show{display:block}
__AI_CSS__
</style>
</head>
<body>
<header class="jl-hud">
  <h1 class="jl-hud-title" id="jl-title">__TITLE_ESC__</h1>
  <div class="jl-hud-stats">
    <span class="jl-pill" id="jl-prog">Câu 0/0</span>
    <span class="jl-pill" id="jl-score">Điểm: 0</span>
    <span class="jl-pill">Chuột luôn sẵn sàng</span>
    <button type="button" class="jl-btn" id="jl-reset">Chơi lại</button>
  </div>
</header>
<div id="jl-err" class="jl-err" role="alert"></div>
<main id="game-stage" class="jl-stage">
__AI_MARKUP__
</main>
__CAM_BOX__
__HAND_CURSOR__
<script>
(function(){
  var USES_HANDS = __USES_HANDS__;
  var initCbs = [], handCbs = [], actionCbs = [], frameCbs = [], resetCbs = [];
  var lastQs = [], lastActionAt = 0;
  var progEl = document.getElementById('jl-prog');
  var scoreEl = document.getElementById('jl-score');
  var errEl = document.getElementById('jl-err');
  var cursorEl = document.getElementById('jl-hand-cursor');

  window.addEventListener('error', function(ev){
    if (errEl) { errEl.textContent = 'Lỗi trò chơi: ' + (ev && ev.message ? ev.message : 'không xác định'); errEl.className = 'jl-err show'; }
  });

  var RT = window.JLRuntime = {
    questions: [],
    onInit: function(fn){ if (typeof fn === 'function') { initCbs.push(fn); if (lastQs.length) fn(lastQs.slice()); } },
    onHand: function(fn){ if (typeof fn === 'function') handCbs.push(fn); },
    onAction: function(fn){ if (typeof fn === 'function') actionCbs.push(fn); },
    onFrame: function(fn){ if (typeof fn === 'function') frameCbs.push(fn); },
    onReset: function(fn){ if (typeof fn === 'function') resetCbs.push(fn); },
    setProgress: function(cur, total){ if (progEl) progEl.textContent = 'Câu ' + cur + '/' + total; },
    setScore: function(score, total){ if (scoreEl) scoreEl.textContent = total != null ? ('Điểm: ' + score + '/' + total) : ('Điểm: ' + score); },
    finish: function(correct, total){ parent.postMessage({ type: 'finish', correct: correct, total: total }, '*'); },
    triggerReset: function(){
      if (errEl) { errEl.className = 'jl-err'; errEl.textContent = ''; }
      resetCbs.forEach(function(fn){ fn(lastQs.slice()); });
      if (!resetCbs.length) initCbs.forEach(function(fn){ fn(lastQs.slice()); });
    }
  };

  document.getElementById('jl-reset').addEventListener('click', function(){ RT.triggerReset(); });

  window.addEventListener('message', function(e){
    var d = e.data;
    if (!d || e.source !== parent) return;
    if (d.type === 'camera.init'){
      lastQs = Array.isArray(d.questions) ? d.questions : [];
      RT.questions = lastQs.slice();
      initCbs.forEach(function(fn){ fn(lastQs.slice()); });
    } else if (d.type === 'camera.hand'){
      var hands = Array.isArray(d.hands) ? d.hands : [];
      var lm = hands[0] || null;
      var indexTip = lm && lm[8] ? { x: lm[8].x, y: lm[8].y } : null;
      var palm = lm && lm[9] ? { x: lm[9].x, y: lm[9].y } : null;
      var pt = indexTip || palm;
      if (cursorEl){
        if (pt){ cursorEl.style.display = 'block'; cursorEl.style.left = (pt.x * 100) + 'vw'; cursorEl.style.top = (pt.y * 100) + 'vh'; }
        else { cursorEl.style.display = 'none'; }
      }
      handCbs.forEach(function(fn){ fn({ hands: hands, indexTip: indexTip, palm: palm, available: !!d.available }); });
    } else if (d.type === 'camera.result'){
      var now = Date.now();
      if (now - lastActionAt < 500) return;
      lastActionAt = now;
      actionCbs.forEach(function(fn){ fn({ input: d.input, label: d.label, confidence: d.confidence }); });
    } else if (d.type === 'camera.frame'){
      frameCbs.forEach(function(fn){ fn(d.scores || {}); });
    }
  });

  try {
    var man = JSON.parse(document.getElementById('jl-camera').textContent || '{}');
    if (man.demo && Array.isArray(man.demo.questions) && man.demo.questions.length){
      lastQs = man.demo.questions;
      RT.questions = lastQs.slice();
    }
  } catch (e) {}

  /* === AI-GENERATED GAMEPLAY === */
__AI_JS__
  /* === END AI-GENERATED GAMEPLAY === */

  if (lastQs.length) { initCbs.forEach(function(fn){ fn(lastQs.slice()); }); }
  parent.postMessage({ type: 'ready' }, '*');
  if (USES_HANDS) { parent.postMessage({ type: 'hands', on: true }, '*'); }
})();
</script>
</body>
</html>""".replace("__TITLE_ESC__", title_esc) \
           .replace("__MANIFEST_JSON__", _safe_json(man)) \
           .replace("__AI_CSS__", css) \
           .replace("__AI_MARKUP__", markup) \
           .replace("__CAM_BOX__", cam_box) \
           .replace("__HAND_CURSOR__", hand_cursor) \
           .replace("__USES_HANDS__", "true" if uses_hands else "false") \
           .replace("__AI_JS__", js)
