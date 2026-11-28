"""P0 AI Composer Capability & Catalog Integration Tests (TC01–TC08).

Kiểm chứng kiến trúc tách Live Registry (Web) vs Frozen Evaluation Registry (CLI/Eval):
- TC01: Built-in MediaPipe Model ("Bàn tay (MediaPipe)", kind=hands) + compatible approved showcase Player
        ("Tết 2027: Dê Vàng và cổng băng", kinds=['hands','image','pose'], inputs=['grab','release'])
        → REUSE → Preview (CSP + actual exam) → Approve → Publish → Play (model.kind='hands') → Reload.
- TC02: Custom Trained/Added Model (image/pose, private to teacher A) → REUSE with Quiz ABCD + valid mapping
        → Publish → Play.
- TC03: Reuse Model + Player with newly generated Exam (`exam.mode='generate_new'`).
- TC04: Mouse-only REUSE (no regression).
- TC05: Incompatible Model + Player (MediaPipe hands + Quiz ABCD, or invalid role/duplicate mapping) → blocked cleanly.
- TC06: Private Model Isolation — Teacher B CANNOT see or use Teacher A's private model in Live Registry or Publish.
- TC07: GENERATE New Player (mouse-only P0 contract preserved, private draft player).
- TC08: Evaluation Isolation — `composer.catalog_snapshot()` & `trusted_registry(include_showcase=False)` remain
        strictly frozen (2 sample players, built-in/public models, built-in exams only; unaffected by showcase/private).
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
import agent_bridge  # noqa: E402
import composer  # noqa: E402
import contract  # noqa: E402
import game_templates  # noqa: E402
import guardrails  # noqa: E402
import server  # noqa: E402
import store  # noqa: E402


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
    head_lines = head_bytes.decode("iso-8859-1").split("\r\n")
    status = int(head_lines[0].split(" ", 2)[1])
    set_cookie = None
    for line in head_lines[1:]:
        if line.lower().startswith("set-cookie:"):
            set_cookie = line.split(":", 1)[1].strip()
            break
    data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    return status, data, set_cookie


class ComposerCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test_cap.db")
        self._orig_db = store.DB_PATH
        store.DB_PATH = self.db_path
        store.init(admin_password="AdminPassword123!")

        st, _, c1 = _req("POST", "/api/register", {"username": "gv_alpha", "password": "Password123!"})
        self.assertEqual(st, 200)
        self.cookie_a = c1.split(";", 1)[0]

        st, _, c2 = _req("POST", "/api/register", {"username": "gv_beta", "password": "Password123!"})
        self.assertEqual(st, 200)
        self.cookie_b = c2.split(";", 1)[0]

        # Find built-in MediaPipe hands model ID and Tết 2027 hands-compatible showcase player ID dynamically (no hardcoding)
        c = store.connect()
        try:
            self.hands_model = dict(c.execute("SELECT * FROM models WHERE kind='hands' LIMIT 1").fetchone())
            self.hands_player = None
            for r in c.execute("SELECT * FROM players WHERE status='approved'").fetchall():
                man = json.loads(r["manifest"])
                # Chọn player hands có input 'grab' (Tết 2027): các test này mock mapping grab/release,
                # trong khi Penalty 3D (cập nhật 28/11) cũng khai kinds hands nhưng inputs A–F.
                if "hands" in (man.get("kinds") or []) and any(i.get("key") == "grab" for i in (man.get("inputs") or [])):
                    self.hands_player = dict(r)
                    break
            self.quiz_player = dict(c.execute("SELECT * FROM players WHERE name='Quiz ABCD bằng cử chỉ'").fetchone())
        finally:
            c.close()
        self.assertIsNotNone(self.hands_player, "Expected an approved hands-compatible player in seeded DB")

    def tearDown(self):
        store.DB_PATH = self._orig_db
        self.tmp.cleanup()

    def test_tc01_builtin_mediapipe_hands_e2e_reuse_publish_play(self):
        """TC01: Built-in MediaPipe hands model pairs with compatible approved showcase player + existing exam."""
        captured_prompts = []

        def _mock_llm(system, user):
            captured_prompts.append(system)
            payload = {
                "decision": "REUSE",
                "message": "Đã chọn trình chơi tương thích với Bàn tay (MediaPipe) kèm bộ đề Toán 12 và Mouse Fallback.",
                "app_name": "Toán 12 bằng Bàn tay",
                "player_id": self.hands_player["id"],
                "model_id": self.hands_model["id"],
                "mapping": {"grab": "fist", "release": "open"},
                "exam_mode": "reuse_existing",
                "exam_id": 1,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 150, "tokens_out": 90}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Tạo game ôn tập Toán 12 dùng model Bàn tay (MediaPipe)"
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "REUSE")
        self.assertEqual(res["application_plan"]["player"]["player_id"], self.hands_player["id"])
        self.assertEqual(res["application_plan"]["model"]["model_id"], self.hands_model["id"])
        self.assertEqual(res["application_plan"]["model"]["mapping"], {"grab": "fist", "release": "open"})
        # Confirm Live Registry exposed the hands-compatible player to the LLM prompt
        self.assertIn(self.hands_player["name"], captured_prompts[0])

        # Preview serves CSP + actual exam questions
        st_prev, prev, _ = _req("GET", res["preview_url"], cookie=self.cookie_a)
        self.assertEqual(st_prev, 200)
        self.assertIn("Content-Security-Policy", prev["srcdoc"])
        self.assertGreater(len(prev["sampleQuestions"]), 2)

        # Publish & Play
        st_pub, pub, _ = _req("POST", "/api/agent/publish", {
            "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
            "approved": True, "reviewed_knowledge": True,
        }, self.cookie_a)
        self.assertEqual(st_pub, 200)
        self.assertGreater(pub["app_id"], 0)

        st_play, play_d, _ = _req("GET", "/api/apps/%d/play" % pub["app_id"], cookie=self.cookie_a)
        self.assertEqual(st_play, 200)
        self.assertEqual(play_d["model"]["kind"], "hands")
        self.assertEqual(play_d["mapping"], {"grab": "fist", "release": "open"})
        self.assertGreater(len(play_d["questions"]), 0)

    def test_tc02_tc03_tc06_custom_private_model_new_exam_and_isolation(self):
        """TC02 + TC03 + TC06: Teacher A creates private image model → REUSE with Quiz ABCD + new exam; Teacher B is isolated."""
        st_m, created_m, _ = _req("POST", "/api/models", {
            "name": "Giơ thẻ ABCD lớp 12A",
            "description": "Model riêng tư của GV Alpha",
            "kind": "image",
            "url": "https://teachablemachine.withgoogle.com/models/demo12345/",
            "outputs": [
                {"key": "A", "role": "action"},
                {"key": "B", "role": "action"},
                {"key": "C", "role": "action"},
                {"key": "D", "role": "action"},
            ],
            "visibility": "private",
        }, self.cookie_a)
        self.assertEqual(st_m, 201)
        custom_mid = created_m["id"]

        # TC02 + TC03: Teacher A uses custom private model + Quiz ABCD + newly generated exam
        def _mock_custom_a(system, user):
            self.assertIn("Giơ thẻ ABCD lớp 12A", system)
            payload = {
                "decision": "REUSE",
                "message": "Ghép model riêng tư của bạn với Quiz ABCD và bộ câu hỏi mới.",
                "app_name": "Quiz với Model riêng",
                "player_id": self.quiz_player["id"],
                "model_id": custom_mid,
                "mapping": {"A": "A", "B": "B", "C": "C", "D": "D"},
                "exam_mode": "generate_new",
                "exam_id": None,
                "exam_content": "2+2=? | 3 | 4 | 5 | 6 | =B\n3+3=? | 5 | 6 | 7 | 8 | =B",
                "expected_question_count": 2,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 130, "tokens_out": 85}

        with mock.patch.object(agent, "call_model", side_effect=_mock_custom_a):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Dùng model Giơ thẻ ABCD lớp 12A với Quiz ABCD và soạn 2 câu Toán"
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "REUSE")
        self.assertEqual(res["application_plan"]["model"]["model_id"], custom_mid)

        st_pub, pub, _ = _req("POST", "/api/agent/publish", {
            "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
            "approved": True, "reviewed_knowledge": True,
        }, self.cookie_a)
        self.assertEqual(st_pub, 200)
        self.assertGreater(pub["exam_id"], 0)

        st_play, play_d, _ = _req("GET", "/api/apps/%d/play" % pub["app_id"], cookie=self.cookie_a)
        self.assertEqual(st_play, 200)
        self.assertEqual(play_d["model"]["kind"], "image")
        self.assertEqual(len(play_d["questions"]), 2)

        # TC06: Teacher B MUST NOT see Teacher A's private model in Live Registry AND cannot use custom_mid!
        def _mock_steal_b(system, user):
            self.assertNotIn("Giơ thẻ ABCD lớp 12A", system)
            payload = {
                "decision": "REUSE",
                "message": "Thử dùng model của người khác",
                "app_name": "Thử truy cập trái phép",
                "player_id": self.quiz_player["id"],
                "model_id": custom_mid,
                "mapping": {"A": "A", "B": "B", "C": "C", "D": "D"},
                "exam_mode": "reuse_existing",
                "exam_id": 1,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 110, "tokens_out": 60}

        with mock.patch.object(agent, "call_model", side_effect=_mock_steal_b):
            st_b, res_b, _ = _req("POST", "/api/agent", {
                "text": "Dùng model id=%d" % custom_mid
            }, self.cookie_b)
        self.assertEqual(st_b, 200)
        self.assertEqual(res_b["decision"], "ERROR")
        self.assertNotIn("draft_id", res_b)

    def test_tc05_incompatible_model_and_player_is_blocked(self):
        """TC05: Pairing MediaPipe hands with Quiz ABCD (kinds=['image','pose']) MUST be rejected by Rules."""
        def _mock_bad_pair(system, user):
            payload = {
                "decision": "REUSE",
                "message": "Thử ghép sai",
                "app_name": "Ghép sai",
                "player_id": self.quiz_player["id"],
                "model_id": self.hands_model["id"],
                "mapping": {"A": "fist", "B": "open"},
                "exam_mode": "reuse_existing",
                "exam_id": 1,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 100, "tokens_out": 50}

        with mock.patch.object(agent, "call_model", side_effect=_mock_bad_pair):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Ép ghép Bàn tay (MediaPipe) vào Quiz ABCD bằng cử chỉ"
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "ERROR")
        self.assertNotIn("draft_id", res)

    def test_tc08_frozen_evaluation_catalog_is_strictly_isolated(self):
        """TC08: Frozen Evaluation Catalog MUST NOT expose showcase players or private user models/exams."""
        # Add private model for Teacher A
        st_m, created_m, _ = _req("POST", "/api/models", {
            "name": "Model Riêng Tư Eval Check",
            "kind": "pose",
            "url": "https://teachablemachine.withgoogle.com/models/private999/",
            "outputs": [{"key": "Left", "role": "action"}, {"key": "Right", "role": "action"}],
            "visibility": "private",
        }, self.cookie_a)
        self.assertEqual(st_m, 201)

        snap = composer.catalog_snapshot()
        player_ids = [p["id"] for p in snap["players"]]
        model_ids = [m["id"] for m in snap["models"]]
        self.assertEqual(len(player_ids), 2)
        self.assertNotIn(self.hands_player["id"], player_ids)
        self.assertNotIn(created_m["id"], model_ids)

        c = store.connect()
        try:
            frozen_reg = agent_bridge.trusted_registry(c, user=None, include_showcase=False)
            self.assertEqual(len(frozen_reg["players"]), 2)
            self.assertNotIn(self.hands_player["id"], [p["id"] for p in frozen_reg["players"]])
            self.assertNotIn(created_m["id"], [m["id"] for m in frozen_reg["models"]])
        finally:
            c.close()

    def test_draft8_regression_llm_silently_drops_mediapipe_model_to_quiz_mouse_only(self):
        """Regression Draft #8 (A01): Even when LLM anchors to Quiz ABCD (id=1) and sets model_id=null,
        deterministic Model-aware REUSE MUST preserve 'Bàn tay (MediaPipe)' and pick the compatible hands player!"""
        def _mock_llm_anchored_to_quiz(system, user):
            payload = {
                "decision": "REUSE",
                "message": "Sử dụng Quiz ABCD bằng cử chỉ nhưng Bàn tay không phù hợp nên dùng chuột.",
                "app_name": "Ôn Toán 12",
                "player_id": self.quiz_player["id"],
                "model_id": None,
                "mapping": {},
                "exam_mode": "reuse_existing",
                "exam_id": 1,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 120, "tokens_out": 80}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm_anchored_to_quiz):
            st, res, _ = _req("POST", "/api/agent", {
                "text": 'Tạo game trắc nghiệm ôn tập Toán 12 dùng bộ đề có sẵn "Toán 12: Đạo hàm và khảo sát hàm số", điều khiển bằng model có sẵn "Bàn tay (MediaPipe)" (và có dự phòng chuột).'
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "REUSE")
        self.assertEqual(res["application_plan"]["player"]["player_id"], self.hands_player["id"])
        self.assertEqual(res["application_plan"]["model"]["model_id"], self.hands_model["id"])
        self.assertEqual(res["application_plan"]["model"]["mapping"], {"grab": "fist", "release": "open"})

    def test_a03_explicit_incompatible_player_and_model_never_silently_swapped(self):
        """A03: When user explicitly names BOTH Quiz ABCD and Bàn tay (MediaPipe), NEVER swap player or drop model."""
        def _mock_llm_drops_model(system, user):
            payload = {
                "decision": "REUSE",
                "message": "Chuyển sang chuột.",
                "app_name": "Quiz chuột",
                "player_id": self.quiz_player["id"],
                "model_id": None,
                "mapping": {},
                "exam_mode": "reuse_existing",
                "exam_id": 1,
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 110, "tokens_out": 60}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm_drops_model):
            st, res, _ = _req("POST", "/api/agent", {
                "text": 'Ghép đích danh model "Bàn tay (MediaPipe)" vào trình chơi "Quiz ABCD bằng cử chỉ" với bộ đề Toán 12.'
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "ERROR")
        self.assertNotIn("draft_id", res)

    def test_a05_matching_cards_template_guided_generate_e2e(self):
        """A05: Matching Cards Hybrid GENERATE produces verified zero-flag HTML + preview + publish + play."""
        def _mock_gen_matching(system, user):
            payload = {
                "decision": "GENERATE",
                "message": "Tạo trò chơi ghép cặp thẻ từ vựng tiếng Anh chủ đề Động vật.",
                "app_name": "Ghép cặp Động vật",
                "exam_mode": "generate_new",
                "exam_content": "Con mèo | Cat | Dog | =A\nCon chó | Bird | Dog | =B\nCon chim | Bird | Fish | =A",
                "expected_question_count": 3,
                "game_idea": "Trò chơi ghép cặp thẻ từ vựng tiếng Anh chủ đề Động vật",
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 130, "tokens_out": 85}

        with mock.patch.object(agent, "call_model", side_effect=_mock_gen_matching):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Tạo trò chơi mới dạng ghép cặp thẻ từ vựng tiếng Anh chủ đề Động vật, 3 câu, chơi bằng chuột"
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "GENERATE")
        self.assertEqual(res["safety_flags"], [])
        self.assertIn("Template-guided (matching_cards)", res["message"])

        st_prev, prev, _ = _req("GET", res["preview_url"], cookie=self.cookie_a)
        self.assertEqual(st_prev, 200)
        self.assertEqual(len(prev["sampleQuestions"]), 3)
        self.assertEqual(prev["manifest"]["questions"], "exam")
        self.assertNotIn("content", prev["manifest"])
        self.assertIn("reset-btn", prev["srcdoc"])

        st_pub, pub, _ = _req("POST", "/api/agent/publish", {
            "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
            "approved": True, "reviewed_knowledge": True,
        }, self.cookie_a)
        self.assertEqual(st_pub, 200)
        self.assertGreater(pub["app_id"], 0)

    def test_a06_true_false_template_guided_generate_e2e(self):
        """A06: True/False Hybrid GENERATE produces verified zero-flag HTML + preview + publish."""
        def _mock_gen_tf(system, user):
            payload = {
                "decision": "GENERATE",
                "message": "Tạo trò chơi Đúng/Sai tốc độ môn Sinh học.",
                "app_name": "Đúng Sai Sinh học",
                "exam_mode": "generate_new",
                "exam_content": "Cá voi là động vật có vú | =Đúng\nCây xanh quang hợp không cần ánh sáng | =Sai",
                "expected_question_count": 2,
                "game_idea": "Trò chơi Đúng/Sai tốc độ môn Sinh học",
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 120, "tokens_out": 80}

        with mock.patch.object(agent, "call_model", side_effect=_mock_gen_tf):
            st, res, _ = _req("POST", "/api/agent", {
                "text": "Tạo mini game Đúng/Sai tốc độ môn Sinh học 2 câu chơi bằng chuột"
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "GENERATE")
        self.assertEqual(res["safety_flags"], [])
        self.assertIn("Template-guided (true_false)", res["message"])

    def test_a09_draft9_conflicting_manifest_and_missing_protocol_blocked(self):
        """Regression Draft #9 (A09): L1 blocks conflicting questions='exam' + content.kind='texts';
        L4 blocks missing camera.init/ready protocol."""
        draft9_bad_html = """<!doctype html><html><head><meta charset="utf-8"><title>Bad</title>
        <script type="application/json" id="jl-camera">
        {"name":"Bad Draft 9","description":"Conflicting manifest","questions":"exam","content":{"kind":"texts","label":"L","min":2,"max":10}}
        </script></head><body><script>window.addEventListener("message",function(e){if(e.data.type==="camera.init"){}});parent.postMessage({type:"ready"},"*");</script></body></html>"""
        vres = guardrails.validate_html_draft(draft9_bad_html)
        self.assertFalse(vres["ok"])
        self.assertIn("xung đột", vres["error"].lower())

        missing_proto_html = """<!doctype html><html><head><meta charset="utf-8"><title>NoProto</title>
        <script type="application/json" id="jl-camera">
        {"name":"NoProto","description":"Missing runtime handshake","questions":"exam"}
        </script></head><body><script>var x = 1;</script></body></html>"""
        vres2 = guardrails.validate_html_draft(missing_proto_html)
        self.assertFalse(vres2["ok"])
        self.assertIn("giao thức runtime", vres2["error"].lower())

    def test_a09_duplicate_and_empty_role_mapping_rejected(self):
        """A09: Mapping validator rejects duplicate output classes and empty-role ('none') mapped to action inputs."""
        dup_comp = composer.validate_compatibility(
            self.hands_player["id"], self.hands_model["id"], 1,
            mapping={"grab": "fist", "release": "fist"},
        )
        self.assertFalse(dup_comp["ok"])

        empty_role_comp = composer.validate_compatibility(
            self.hands_player["id"], self.hands_model["id"], 1,
            mapping={"grab": "fist", "release": "none"},
        )
        self.assertFalse(empty_role_comp["ok"])

    def test_info_rescue_when_llm_returns_info_for_builtin_mediapipe_hands(self):
        """Regression UAT: When LLM returns decision='INFO' claiming Quiz ABCD lacks hands,
        Web Live Registry has an approved hands-compatible player → rescued deterministically to REUSE."""
        def _mock_llm_info(system, user):
            payload = {
                "decision": "INFO",
                "message": 'Model "Bàn tay (MediaPipe)" không tương thích với "Quiz ABCD bằng cử chỉ" vì thiếu hands.',
            }
            return {"text": "```json\n%s\n```" % json.dumps(payload, ensure_ascii=False),
                    "model": "gpt-4o-mini", "tokens_in": 120, "tokens_out": 60}

        with mock.patch.object(agent, "call_model", side_effect=_mock_llm_info):
            st, res, _ = _req("POST", "/api/agent", {
                "text": 'Tạo game trắc nghiệm ôn tập Toán 12 dùng bộ đề có sẵn "Toán 12: Đạo hàm và khảo sát hàm số", điều khiển bằng model có sẵn "Bàn tay (MediaPipe)".'
            }, self.cookie_a)
        self.assertEqual(st, 200)
        self.assertEqual(res["decision"], "REUSE")
        self.assertEqual(res["application_plan"]["player"]["player_id"], self.hands_player["id"])
        self.assertEqual(res["application_plan"]["model"]["model_id"], self.hands_model["id"])
        self.assertEqual(res["application_plan"]["model"]["mapping"], {"grab": "fist", "release": "open"})
        self.assertEqual(res["application_plan"]["exam"]["exam_id"], 1)

    def test_normalize_exam_lines_fixes_literal_answer_and_truefalse_columns(self):
        """Regression UAT: LLM outputs '=Cat' or '| Đúng | Sai | =Đúng' → normalized cleanly to '=A' before parse_questions."""
        raw = (
            "1. Con mèo tiếng Anh là gì? | Cat | Dog | Bird | Fish | =Cat\n"
            "2. Cá voi là động vật có vú | Đúng | Sai | =Đúng\n"
            "3. Trái đất hình vuông | Đúng | Sai | =Sai"
        )
        norm = agent._normalize_exam_lines(raw)
        qs = store.parse_questions(norm)
        self.assertEqual(len(qs), 3)
        self.assertEqual([q["answer"] for q in qs], ["A", "A", "B"])


if __name__ == "__main__":
    unittest.main()
