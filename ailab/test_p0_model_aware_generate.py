"""Phase 3 & 4 — Spec-driven Model-aware GENERATE Tests (PoC 1–4 & Negative Cases).

Kiểm chứng toàn bộ luồng Spec-driven Model-aware GENERATE (không gọi API trả phí, không sửa DB thật):
- PoC 1: MediaPipe Hands (Thu hoạch táo phép nhân lớp 3, 5 câu mới) → GENERATE (không REUSE showcase),
         model.kind='hands', mapping={'grab':'fist','release':'open'}, camera.hand + camera.result + Mouse Fallback,
         Preview → HITL → Publish (draft/private) → Play → Reload.
- PoC 2: MediaPipe Hands (Chỉ ngón tay vào 4 hành tinh Hệ Mặt Trời lớp 5, 4 câu mới) → cơ chế khác PoC 1,
         dùng landmark ngón trỏ lm[8] + chống chọn lặp.
- PoC 3: Mouse-only Free-form Regression (kéo thả phân loại động vật) — không bị ép vào Matching Cards / True-False.
- PoC 4: Custom trained Pose/Image Model (fixture) → GENERATE player bind đúng model riêng tư + cô lập giữa user.
- Negative Cases: GameSpec mismatch (thiếu camera.hand) được sửa TẤT ĐỊNH bởi Runtime Wrapper (không cần lượt sinh lại);
                  audio model bị chặn trung thực; Frozen Evaluation Catalog (`composer.catalog_snapshot()`) hoàn toàn cách ly.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "codebase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402
import composer  # noqa: E402
import game_spec  # noqa: E402
import server  # noqa: E402
import store  # noqa: E402

POC1_HANDS_APPLE_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Thu hoạch táo phép nhân</title>
<script type="application/json" id="jl-camera">
{"name":"Thu hoạch táo phép nhân","description":"Di chuyển giỏ bằng tay, nắm tay hái táo hoặc click chuột","kinds":["hands"],"inputs":[{"key":"grab","label":"Nắm tay chọn","required":true,"accepts":["action"]},{"key":"release","label":"Xòe tay thả","required":false,"accepts":["action"]}],"questions":"exam"}
</script></head>
<body>
<div data-jl-camera></div>
<h1 id="q">Đang nạp...</h1><div id="apples"></div><div id="score">0</div>
<button id="reset">Chơi lại</button>
<script>
var qs=[], idx=0, score=0, cursorX=0.5, locked=false;
function render(){
  if(idx>=qs.length){ document.getElementById('q').textContent='Xong '+score+'/'+qs.length; parent.postMessage({type:'finish',correct:score,total:qs.length},'*'); return; }
  var q=qs[idx]; document.getElementById('q').textContent=q.text;
  var box=document.getElementById('apples'); box.innerHTML='';
  (q.choices||[]).forEach(function(c){
    var b=document.createElement('button'); b.textContent=c.key+'. '+c.text; b.dataset.k=c.key;
    b.addEventListener('click',function(){ pick(c.key); }); box.appendChild(b);
  });
}
function pick(k){ if(locked||idx>=qs.length)return; locked=true; if(k===qs[idx].answer)score++; document.getElementById('score').textContent=String(score); idx++; locked=false; render(); }
document.getElementById('reset').addEventListener('click',function(){ idx=0; score=0; render(); });
window.addEventListener('message',function(e){
  var d=e.data; if(!d||e.source!==parent)return;
  if(d.type==='camera.init'){ qs=d.questions||[]; idx=0; score=0; render(); }
  if(d.type==='camera.hand'&&d.hands&&d.hands[0]&&d.hands[0][9]){ cursorX=d.hands[0][9].x; }
  if(d.type==='camera.result'&&d.input==='grab'&&qs[idx]){ var ch=qs[idx].choices||[]; if(ch.length){ pick(ch[Math.min(ch.length-1,Math.floor(cursorX*ch.length))].key); } }
});
parent.postMessage({type:'ready'},'*');
parent.postMessage({type:'hands',on:true},'*');
</script></body></html>"""

POC2_HANDS_PLANETS_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Chỉ tay hành tinh Hệ Mặt Trời</title>
<script type="application/json" id="jl-camera">
{"name":"Chỉ tay hành tinh","description":"Chỉ ngón trỏ vào 1 trong 4 hành tinh hoặc click chuột","kinds":["hands"],"inputs":[{"key":"grab","label":"Nắm tay chọn","required":true,"accepts":["action"]},{"key":"release","label":"Xòe tay thả","required":false,"accepts":["action"]}],"questions":"exam"}
</script></head>
<body>
<div data-jl-camera></div><h1 id="q"></h1><div id="planets"></div><button id="reset">Chơi lại</button>
<script>
var qs=[], idx=0, score=0, lastPickAt=0, dwellKey=null, dwellSince=0;
function render(){ if(idx>=qs.length){ parent.postMessage({type:'finish',correct:score,total:qs.length},'*'); return; } document.getElementById('q').textContent=qs[idx].text; }
function confirmPick(k){ var now=Date.now(); if(now-lastPickAt<900||idx>=qs.length)return; lastPickAt=now; if(k===qs[idx].answer)score++; idx++; render(); }
document.getElementById('reset').addEventListener('click',function(){ idx=0; score=0; dwellKey=null; render(); });
window.addEventListener('message',function(e){
  var d=e.data; if(!d||e.source!==parent)return;
  if(d.type==='camera.init'){ qs=d.questions||[]; idx=0; score=0; render(); }
  if(d.type==='camera.hand'&&d.hands&&d.hands[0]&&d.hands[0][8]){ var tip=d.hands[0][8]; var k=['A','B','C','D'][Math.min(3,Math.floor(tip.x*4))]; if(k!==dwellKey){ dwellKey=k; dwellSince=Date.now(); } else if(Date.now()-dwellSince>650){ confirmPick(k); dwellKey=null; } }
});
parent.postMessage({type:'ready'},'*');
parent.postMessage({type:'hands',on:true},'*');
</script></body></html>"""

POC3_FREEFORM_CLASSIFY_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Phân loại Động vật</title>
<script type="application/json" id="jl-camera">
{"name":"Phân loại Động vật","description":"Kéo thả hoặc bấm phân loại động vật có xương sống và không xương sống","questions":"exam"}
</script></head>
<body><h1 id="q"></h1><div id="bins"></div><button id="reset">Chơi lại</button>
<script>
var qs=[], idx=0, score=0;
function render(){ if(idx>=qs.length){ parent.postMessage({type:'finish',correct:score,total:qs.length},'*'); return; } document.getElementById('q').textContent=qs[idx].text; }
document.getElementById('reset').addEventListener('click',function(){ idx=0; score=0; render(); });
window.addEventListener('message',function(e){ var d=e.data; if(!d||e.source!==parent)return; if(d.type==='camera.init'){ qs=d.questions||[]; idx=0; score=0; render(); } });
parent.postMessage({type:'ready'},'*');
</script></body></html>"""

POC4_CUSTOM_POSE_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Né chướng ngại vật tư thế</title>
<script type="application/json" id="jl-camera">
{"name":"Né chướng ngại vật tư thế","description":"Nghiêng trái/phải theo model tư thế hoặc click chuột","kinds":["pose"],"inputs":[{"key":"trai","label":"Trai","required":true,"accepts":["action"]},{"key":"phai","label":"Phai","required":true,"accepts":["action"]}],"questions":"exam"}
</script></head>
<body><div data-jl-camera></div><h1 id="q"></h1><button id="reset">Chơi lại</button>
<script>
var qs=[], idx=0, score=0;
function render(){ if(idx>=qs.length){ parent.postMessage({type:'finish',correct:score,total:qs.length},'*'); return; } document.getElementById('q').textContent=qs[idx].text; }
window.addEventListener('message',function(e){ var d=e.data; if(!d||e.source!==parent)return; if(d.type==='camera.init'){ qs=d.questions||[]; idx=0; score=0; render(); } if(d.type==='camera.result'&&qs[idx]){ idx++; render(); } });
parent.postMessage({type:'ready'},'*');
</script></body></html>"""


def _req(method, path, body=None, cookie=None):
    raw_in = json.dumps(body).encode("utf-8") if body is not None else b""
    hdrs = Message()
    hdrs["Content-Length"] = str(len(raw_in))
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if cookie:
        hdrs["Cookie"] = cookie
    out_buf = io.BytesIO()
    h = server.H.__new__(server.H)
    h.path = path
    h.command = method
    h.request_version = "HTTP/1.1"
    h.requestline = "%s %s HTTP/1.1" % (method, path)
    h.log_message = lambda *a: None
    h.headers = hdrs
    h.rfile = io.BytesIO(raw_in)
    h.wfile = out_buf
    h.client_address = ("127.0.0.1", 0)
    h._headers_buffer = []
    h._handle(method)
    raw_out = out_buf.getvalue()
    head_bytes, _, body_bytes = raw_out.partition(b"\r\n\r\n")
    status = int(head_bytes.decode("iso-8859-1").split("\r\n")[0].split(" ", 2)[1])
    set_cookie = None
    for line in head_bytes.decode("iso-8859-1").split("\r\n")[1:]:
        if line.lower().startswith("set-cookie:"):
            set_cookie = line.split(":", 1)[1].strip()
            break
    return status, (json.loads(body_bytes.decode("utf-8")) if body_bytes else {}), set_cookie


class ModelAwareGenerateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test_ma_gen.db")
        self._orig_db = store.DB_PATH
        store.DB_PATH = self.db_path
        store.init(admin_password="AdminPassword123!")

        st, _, c1 = _req("POST", "/api/register", {"username": "teacher_poc", "password": "Password123!"})
        self.assertEqual(st, 200)
        self.cookie_a = c1.split(";", 1)[0]

        st, _, c2 = _req("POST", "/api/register", {"username": "teacher_other", "password": "Password123!"})
        self.assertEqual(st, 200)
        self.cookie_b = c2.split(";", 1)[0]

    def tearDown(self):
        store.DB_PATH = self._orig_db
        self.tmp.cleanup()

    def test_poc1_mediapipe_hands_apple_harvest_generate_publish_play(self):
        """PoC 1: Even if LLM initially suggests REUSE, explicit new-game intent routes to Spec-driven Model-aware GENERATE."""
        prompt = (
            "Tạo một trò chơi mới thu hoạch táo ôn tập phép nhân lớp 3 gồm 5 câu hỏi mới. "
            "Học sinh di chuyển bàn tay để chọn quả táo mang đáp án đúng, nắm tay để hái và có chuột dự phòng. "
            "Sử dụng Model Bàn tay MediaPipe có sẵn. Không sử dụng Player có sẵn."
        )
        five_qs = (
            "3 x 4 = ? | 10 | 12 | 14 | 16 | =B\n"
            "6 x 5 = ? | 25 | 30 | 35 | 40 | =B\n"
            "7 x 3 = ? | 21 | 24 | 27 | 18 | =A\n"
            "8 x 4 = ? | 28 | 30 | 32 | 36 | =C\n"
            "9 x 2 = ? | 16 | 18 | 20 | 22 | =B"
        )
        calls = []

        def _mock_llm(system, user):
            calls.append((system, user))
            if "ĐỊNH DẠNG ĐẦU RA" in system:
                # Even if LLM tried REUSE, Intent Policy MUST override to GENERATE!
                return {"text": "```json\n%s\n```" % json.dumps({
                    "decision": "REUSE",
                    "message": "Thử REUSE",
                    "app_name": "Thu hoạch táo phép nhân",
                    "player_id": 6,
                    "model_id": 1,
                    "exam_mode": "generate_new",
                    "exam_content": five_qs,
                    "expected_question_count": 5,
                    "game_idea": "Thu hoạch táo rơi bằng cử chỉ tay",
                }, ensure_ascii=False), "model": "gpt-4o-mini", "tokens_in": 150, "tokens_out": 100}
            # Verify GameSpec + camera.hand protocol was injected into generator prompt!
            self.assertIn("GAMESPEC BẮT BUỘC TUÂN THỦ", user)
            self.assertIn("camera.hand", user)
            return {"text": "Game thu hoạch táo mới.\n```html\n%s\n```" % POC1_HANDS_APPLE_HTML,
                    "model": "gpt-4o-mini", "tokens_in": 300, "tokens_out": 500}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm):
            st, res, _ = _req("POST", "/api/agent", {"text": prompt}, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "GENERATE")
        self.assertEqual(res["application_plan"]["player"]["mode"], "generate_new")
        self.assertIsNone(res["application_plan"]["player"]["player_id"])
        self.assertEqual(res["application_plan"]["model"]["kind"], "hands")
        self.assertEqual(res["application_plan"]["model"]["mapping"], {"grab": "fist", "release": "open"})
        self.assertEqual(res["application_plan"]["interaction"]["primary"], "hands")
        self.assertTrue(res["application_plan"]["interaction"]["mouse_always_enabled"])
        self.assertEqual(res["safety_flags"], [])

        # Preview has CSP + all 5 multiplication questions
        st_prev, prev, _ = _req("GET", res["preview_url"], cookie=self.cookie_a)
        self.assertEqual(st_prev, 200)
        self.assertEqual(len(prev["sampleQuestions"]), 5)
        self.assertIn("Content-Security-Policy", prev["srcdoc"])

        # HITL Publish → Play → Reload
        st_pub, pub, _ = _req("POST", "/api/agent/publish", {
            "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
            "approved": True, "reviewed_knowledge": True,
        }, self.cookie_a)
        self.assertEqual(st_pub, 200)
        self.assertGreater(pub["app_id"], 0)
        self.assertEqual(pub["share"], 0)

        st_play, play_d, _ = _req("GET", "/api/apps/%d/play" % pub["app_id"], cookie=self.cookie_a)
        self.assertEqual(st_play, 200)
        self.assertEqual(play_d["model"]["kind"], "hands")
        self.assertEqual(play_d["mapping"], {"grab": "fist", "release": "open"})
        self.assertEqual(len(play_d["questions"]), 5)

    def test_poc2_mediapipe_hands_planets_and_deterministic_protocol_repair(self):
        """PoC 2 (UAT blocker): LLM viết sai protocol hands ở MỌI lượt → Runtime Wrapper vẫn lắp Player hợp lệ
        (manifest từ GameSpec, gửi {type:'hands',on:true}, đọc d.hands trong camera.hand) mà không cần lượt sinh lại."""
        prompt = (
            "Tạo một trò chơi mới chọn đáp án bằng cách chỉ ngón tay vào một trong bốn hành tinh trên màn hình. "
            "Chủ đề hệ Mặt Trời lớp 5, gồm 4 câu hỏi mới. Dùng MediaPipe Hands và chuột dự phòng."
        )
        four_qs = (
            "Hành tinh nào gần Mặt Trời nhất? | Sao Thủy | Sao Kim | Trái Đất | Sao Hỏa | =A\n"
            "Hành tinh nào lớn nhất? | Sao Thổ | Sao Mộc | Sao Thiên Vương | Sao Hải Vương | =B\n"
            "Hành tinh nào có màu đỏ? | Sao Kim | Trái Đất | Sao Hỏa | Sao Thủy | =C\n"
            "Hành tinh nào có vành đai nổi bật? | Sao Thổ | Sao Thủy | Sao Hỏa | Sao Kim | =A"
        )
        bad_html = POC2_HANDS_PLANETS_HTML.replace("camera.hand", "noop").replace("'hands'", "'none'")
        gen_attempts = {"n": 0}

        def _mock_llm(system, user):
            if "ĐỊNH DẠNG ĐẦU RA" in system:
                return {"text": "```json\n%s\n```" % json.dumps({
                    "decision": "GENERATE",
                    "message": "Tạo game chỉ tay chọn hành tinh.",
                    "app_name": "Chỉ tay hành tinh",
                    "exam_mode": "generate_new",
                    "exam_content": four_qs,
                    "expected_question_count": 4,
                    "game_idea": "Chỉ ngón tay vào 4 hành tinh trên màn hình",
                }, ensure_ascii=False), "model": "gpt-4o-mini", "tokens_in": 140, "tokens_out": 90}
            gen_attempts["n"] += 1
            # LLM CỨNG viết sai protocol ở mọi lượt (đúng kịch bản UAT thất bại trước đây)
            return {"text": "Thiếu camera.hand.\n```html\n%s\n```" % bad_html,
                    "model": "gpt-4o-mini", "tokens_in": 200, "tokens_out": 300}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm):
            st, res, _ = _req("POST", "/api/agent", {"text": prompt}, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(gen_attempts["n"], 1)  # sửa tất định — không tốn lượt gọi model thứ 2
        self.assertEqual(res["decision"], "GENERATE")
        plan = res["application_plan"]
        self.assertEqual(plan["model"]["kind"], "hands")
        self.assertEqual(plan["model"]["mapping"], {"grab": "fist", "release": "open"})
        # Lấy HTML thật của bản nháp qua preview sandbox (srcdoc đã chèn CSP + HELPER)
        st_prev, prev, _ = _req("GET", res["preview_url"], cookie=self.cookie_a)
        self.assertEqual(st_prev, 200)
        html = prev["srcdoc"]
        # Protocol runtime do Wrapper kiểm soát: manifest đúng GameSpec + handshake hands + camera.hand + ô camera
        self.assertIn("window.JLRuntime", html)
        self.assertIn("camera.hand", html)
        self.assertIn("type: 'hands', on: true", html)
        self.assertIn("data-jl-camera", html)
        self.assertIn('id="jl-camera"', html)
        # Gameplay do AI sinh (markup sân chơi + logic dwell chống chọn lặp) vẫn được giữ nguyên trong Player cuối
        self.assertIn('id="planets"', html)
        self.assertIn("dwellSince", html)
        self.assertIn("hành tinh", html.lower())

    def test_poc3_mouse_only_freeform_not_forced_into_matching_or_true_false(self):
        """PoC 3: Free-form mouse-only classification game stays Free-form (not forced into Matching/True-False)."""
        def _mock_llm(system, user):
            if "ĐỊNH DẠNG ĐẦU RA" in system:
                return {"text": "```json\n%s\n```" % json.dumps({
                    "decision": "GENERATE",
                    "message": "Tạo game kéo thả phân loại động vật.",
                    "app_name": "Phân loại Động vật",
                    "exam_mode": "generate_new",
                    "exam_content": "Cá chép thuộc nhóm nào? | Có xương sống | Không xương sống | =A\nGiun đất thuộc nhóm nào? | Có xương sống | Không xương sống | =B",
                    "expected_question_count": 2,
                    "game_idea": "Kéo thả phân loại động vật có xương sống và không xương sống",
                }, ensure_ascii=False), "model": "gpt-4o-mini", "tokens_in": 120, "tokens_out": 80}
            return {"text": "Game phân loại.\n```html\n%s\n```" % POC3_FREEFORM_CLASSIFY_HTML,
                    "model": "gpt-4o-mini", "tokens_in": 200, "tokens_out": 280}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Tạo trò chơi mới kéo thả phân loại động vật có xương sống và không xương sống, chơi bằng chuột."
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "GENERATE")
        self.assertIsNone(res["application_plan"]["model"])
        self.assertIn("Spec-driven Free-form HTML", res["message"])

    def test_poc4_custom_private_pose_model_generate_and_isolation(self):
        """PoC 4 (Fixture): Teacher A's private pose model binds to a newly generated player; Frozen Eval stays isolated."""
        st_m, cm, _ = _req("POST", "/api/models", {
            "name": "Tư thế Nghiêng Trái Phải",
            "kind": "pose",
            "url": "https://teachablemachine.withgoogle.com/models/posefixture1/",
            "outputs": [{"key": "Trai", "role": "action"}, {"key": "Phai", "role": "action"}],
            "visibility": "private",
        }, self.cookie_a)
        self.assertEqual(st_m, 201)
        mid = cm["id"]

        def _mock_llm(system, user):
            if "ĐỊNH DẠNG ĐẦU RA" in system:
                return {"text": "```json\n%s\n```" % json.dumps({
                    "decision": "GENERATE",
                    "message": "Tạo game né chướng ngại vật bằng model tư thế.",
                    "app_name": "Né chướng ngại vật tư thế",
                    "model_id": mid,
                    "exam_mode": "reuse_existing",
                    "exam_id": 1,
                    "game_idea": "Né chướng ngại vật bằng tư thế nghiêng trái phải",
                }, ensure_ascii=False), "model": "gpt-4o-mini", "tokens_in": 140, "tokens_out": 90}
            return {"text": "Game tư thế.\n```html\n%s\n```" % POC4_CUSTOM_POSE_HTML,
                    "model": "gpt-4o-mini", "tokens_in": 210, "tokens_out": 300}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm):
            st, res, _ = _req("POST", "/api/agent", {
                "text": 'Tạo trò chơi mới né chướng ngại vật dùng model "Tư thế Nghiêng Trái Phải" với bộ đề "Toán 12: Đạo hàm và khảo sát hàm số".'
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "GENERATE")
        self.assertEqual(res["application_plan"]["model"]["model_id"], mid)
        self.assertEqual(res["application_plan"]["model"]["kind"], "pose")
        self.assertEqual(res["application_plan"]["model"]["mapping"], {"trai": "Trai", "phai": "Phai"})

        # Frozen Evaluation Snapshot MUST NOT include the private pose model or any generated draft player
        snap = composer.catalog_snapshot()
        self.assertNotIn(mid, [m["id"] for m in snap["models"]])
        self.assertEqual(len(snap["players"]), 2)

    def test_player_assembler_wraps_jlruntime_snippet_with_deterministic_manifest(self):
        """Player Assembler: wraps an AI-generated JLRuntime snippet into a valid, 0-flag, GameSpec-compliant HTML."""
        import guardrails
        import player_assembler
        c = store.connect()
        try:
            hm = dict(c.execute("SELECT * FROM models WHERE kind='hands' LIMIT 1").fetchone())
            hm["outputs"] = json.loads(hm["outputs"])
        finally:
            c.close()
        spec = game_spec.build_game_spec(
            {"app_name": "Hái sao bằng tay", "game_idea": "Di chuyển bàn tay chọn sao đáp án"},
            {"message": "Tạo trò chơi mới hái sao bằng Bàn tay (MediaPipe)"},
            {"models": [hm], "players": [], "exams": []},
            explicit_model=hm,
        )
        snippet = """<style>.star{padding:12px;margin:8px;border-radius:10px}</style>
<h2 id="q"></h2><div id="stars"></div>
<script>
var qs=[], i=0, sc=0;
JLRuntime.onInit(function(list){ qs=list; i=0; sc=0; JLRuntime.setScore(0, qs.length); });
JLRuntime.onHand(function(h){ if(h.palm){ window._x = h.palm.x; } });
JLRuntime.onAction(function(a){ if(a.input==='grab'){ sc++; JLRuntime.setScore(sc, qs.length); } });
</script>"""
        full_html = player_assembler.assemble_player(spec, snippet)
        vres = guardrails.validate_html_draft(full_html)
        self.assertTrue(vres["ok"], vres.get("error"))
        self.assertEqual(game_spec.validate_html_against_spec(full_html, spec), [])
        self.assertIn("window.JLRuntime", full_html)
        self.assertIn("data-jl-camera", full_html)


if __name__ == "__main__":
    unittest.main()
