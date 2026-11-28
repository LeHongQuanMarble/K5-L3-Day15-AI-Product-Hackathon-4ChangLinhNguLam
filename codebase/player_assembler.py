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
    """Tách (css, markup, js) từ đoạn gameplay AI sinh (hỗ trợ cả mảnh HTML lẫn file HTML đầy đủ).

    Markup được làm sạch: bỏ khối manifest jl-camera, bỏ mọi hộp camera AI tự vẽ
    (`data-jl-camera`) — Runtime Wrapper là chủ thể DUY NHẤT hiển thị camera/micro
    (Single Source of Truth, tránh hai MediaStream/hai khung camera trùng nhau).
    """
    text = (raw_snippet or "").strip()
    css_parts = [m.group(1).strip() for m in _STYLE_RE.finditer(text)]
    js_parts = [m.group(1).strip() for m in _SCRIPT_RE.finditer(text)]
    # AI CSS không được đóng sớm thẻ <style> của Wrapper (chống thoát khỏi style để chèn thẻ khác):
    # `<\/style>` khiến browser không đóng thẻ mà CSS parser bỏ qua như selector lỗi.
    css_parts = [re.sub(r"</(\s*style)", r"<\\/\1", c, flags=re.I) for c in css_parts]
    body_m = _BODY_RE.search(text)
    markup = body_m.group(1) if body_m else text
    markup = _STYLE_RE.sub("", markup)
    markup = _SCRIPT_RE.sub("", markup)
    markup = re.sub(r"<script\b[^>]*application/json[^>]*>.*?</script>", "", markup, flags=re.S | re.I)
    markup = re.sub(r"<!doctype[^>]*>|</?(?:html|head|meta|title|body)[^>]*>", "", markup, flags=re.I).strip()
    # Camera do Wrapper sở hữu: AI chỉ nhận dữ liệu qua JLRuntime events
    markup = re.sub(r"\s+data-jl-camera(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+))?", "", markup, flags=re.I)
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

_TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE_ESC__</title>
<script type="application/json" id="jl-camera">
__MANIFEST_JSON__
</script>
<style>
  /* === JL DESIGN SYSTEM (dùng chung cho Player sinh mới — AI dùng lại class, không tự dựng HUD) === */
  :root{
    --jl-bg:#0b1220; --jl-surface:#141d31; --jl-surface-2:#1c2947; --jl-line:rgba(148,163,184,.22);
    --jl-text:#f1f5f9; --jl-muted:#94a3b8;
    --jl-brand:#6366f1; --jl-brand-strong:#4f46e5; --jl-ok:#22c55e; --jl-ok-soft:rgba(34,197,94,.16);
    --jl-bad:#ef4444; --jl-bad-soft:rgba(239,68,68,.16); --jl-gold:#facc15; --jl-sky:#38bdf8;
    --jl-radius:14px; --jl-radius-sm:10px; --jl-space:14px; --jl-font:system-ui,-apple-system,'Segoe UI',sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:var(--jl-font);background:radial-gradient(1200px 700px at 80% -10%,rgba(99,102,241,.18),transparent 60%),var(--jl-bg);color:var(--jl-text);min-height:100vh;display:flex;flex-direction:column}
  .jl-hud{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 18px;background:rgba(20,29,49,.9);border-bottom:1px solid var(--jl-line);backdrop-filter:blur(4px)}
  .jl-hud-title{font-size:16px;font-weight:800;margin:0;letter-spacing:.2px}
  .jl-hud-stats{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .jl-pill{padding:5px 12px;border-radius:999px;background:rgba(99,102,241,.2);color:#e0e7ff;font-size:13px;font-weight:700}
  .jl-btn{padding:10px 20px;border:0;border-radius:var(--jl-radius-sm);background:var(--jl-brand-strong);color:#fff;font-size:14px;font-weight:700;cursor:pointer;transition:transform .12s ease,box-shadow .12s ease,background .12s ease;box-shadow:0 4px 14px rgba(79,70,229,.35)}
  .jl-btn:hover{background:#4338ca;transform:translateY(-1px)}
  .jl-btn:active{transform:translateY(0)}
  .jl-btn.ghost{background:transparent;border:1px solid var(--jl-line);box-shadow:none;color:var(--jl-text)}
  .jl-stage{position:relative;flex:1;min-height:420px;padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden}
  /* Ốp camera/micro duy nhất (Wrapper sở hữu) */
  .jl-cam-pip{position:fixed;right:12px;bottom:12px;width:168px;height:126px;border-radius:12px;overflow:hidden;background:#020617;border:2px solid rgba(255,255,255,.18);z-index:20;box-shadow:0 6px 18px rgba(2,6,23,.5)}
  .jl-cam-pip canvas{width:100%;height:100%;object-fit:cover;display:block}
  .jl-hand-cursor{position:fixed;width:26px;height:26px;border-radius:50%;border:3px solid var(--jl-sky);background:rgba(56,189,248,.28);pointer-events:none;transform:translate(-50%,-50%);display:none;z-index:30;box-shadow:0 0 0 3px rgba(56,189,248,.15)}
  /* Thành phần trả lời — AI thêm class jl-opt vào ô đáp án của mình */
  .jl-opt{padding:14px 18px;margin:8px 0;border-radius:var(--jl-radius);background:var(--jl-surface);border:1px solid var(--jl-line);font-size:16px;font-weight:600;cursor:pointer;transition:background .15s ease,border-color .15s ease,transform .12s ease;min-width:min(420px,86vw);text-align:left}
  .jl-opt:hover{background:var(--jl-surface-2);border-color:rgba(99,102,241,.5);transform:translateY(-1px)}
  .jl-opt.is-picked{border-color:var(--jl-brand);box-shadow:0 0 0 2px rgba(99,102,241,.35)}
  .jl-opt.is-good{background:var(--jl-ok-soft);border-color:var(--jl-ok)}
  .jl-opt.is-bad{background:var(--jl-bad-soft);border-color:var(--jl-bad)}
  /* Màn hình bắt đầu / kết thúc */
  .jl-screen{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;background:rgba(11,18,32,.86);z-index:15;text-align:center;padding:24px;border-radius:var(--jl-radius)}
  .jl-screen h2{margin:0;font-size:26px;font-weight:800}
  .jl-screen p{margin:0;color:var(--jl-muted);font-size:15px;max-width:520px}
  .jl-err{display:none;margin:12px;padding:12px 16px;border-radius:var(--jl-radius-sm);background:#450a0a;color:#fecaca;font-size:14px;border:1px solid rgba(239,68,68,.4)}
  .jl-err.show{display:block}
  .jl-fadein{animation:jl-fade .28s ease both}
  @keyframes jl-fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
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
      RT.setProgress(0, lastQs.length);
      RT.setScore(0, lastQs.length);
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
</html>"""

_PLACEHOLDER_RE = re.compile(
    r"__(?:TITLE_ESC|MANIFEST_JSON|AI_CSS|AI_MARKUP|CAM_BOX|HAND_CURSOR|USES_HANDS|AI_JS)__")


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

    # Thay placeholder MỘT lượt (single-pass): nội dung AI chèn vào không bị các lần replace sau đụng tới,
    # kể cả khi gameplay/manifiest vô tình chứa chữ giống placeholder.
    values = {
        "__TITLE_ESC__": title_esc,
        "__MANIFEST_JSON__": _safe_json(man),
        "__AI_CSS__": css,
        "__AI_MARKUP__": markup,
        "__CAM_BOX__": cam_box,
        "__HAND_CURSOR__": hand_cursor,
        "__USES_HANDS__": "true" if uses_hands else "false",
        "__AI_JS__": js,
    }
    return _PLACEHOLDER_RE.sub(lambda m: values[m.group(0)], _TEMPLATE)
