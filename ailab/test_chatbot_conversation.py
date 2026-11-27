"""C02 — kiểm hội thoại nhiều lượt (chế độ giả có nhãn + model giả lập lỗi). Không DB, không mạng.
python -m unittest discover -s ailab -p "test_*.py"   — mã tình huống: docs/chatbot/C02_SPEC.md"""
import itertools
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbot import conversation as C  # noqa: E402
from chatbot import schemas as S  # noqa: E402
from chatbot import workflow as W  # noqa: E402


def ids():
    n = itertools.count(1)
    return lambda: "p-test%03d" % next(n)


def ctx(**kw):
    d = {"new_id": ids()}
    d.update(kw)
    return d


def turn(text, state=None, context=None, **req):
    r = {"text": text}
    r.update(req)
    return W.process_turn(r, state if state is not None else S.new_state(), context or ctx())


def chat(*texts, context=None):
    c = context or ctx()
    st, out = S.new_state(), []
    for t in texts:
        st, reply, meta = W.process_turn({"text": t}, st, c)
        out.append((st, reply, meta))
    return out


class FakeModel:
    """Model giả lập cho test (KHÔNG phải AI thật): trả lần lượt các câu trả lời đã định, đếm số lời gọi."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), 0

    def __call__(self, system, user):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return {"text": r if isinstance(r, str) else json.dumps(r, ensure_ascii=False), "model": "mock-model",
                "tokens_in": 1, "tokens_out": 1}


class Clarify(unittest.TestCase):
    def test_c02_01_vague_request_asks_missing_only(self):
        st, reply, meta = turn("Tạo game ôn toán")
        self.assertEqual(st["status"], "clarifying")
        self.assertEqual(st["requirements"]["subject"], "Toán")
        self.assertEqual(st["missingFields"], ["gradeOrAudience", "topic"])
        self.assertEqual([q["field"] for q in st["questions"]], ["gradeOrAudience", "topic"])
        self.assertIsNone(st["proposal"])
        self.assertNotIn("môn học nào", reply)
        self.assertEqual(st["version"], 1)

    def test_c02_02_three_turns_no_repeat(self):
        (s1, r1, _), (s2, r2, _), (s3, r3, _) = chat("Tạo game ôn toán", "lớp 2", "phép cộng trong phạm vi 100, 10 câu")
        self.assertEqual(s2["missingFields"], ["topic"])
        self.assertNotIn("lớp mấy", r2)
        self.assertEqual(s3["status"], "awaiting_confirmation")
        req = s3["requirements"]
        self.assertEqual((req["subject"], req["gradeOrAudience"], req["topic"], req["questionCount"]),
                         ("Toán", "Lớp 2", "phép cộng trong phạm vi 100", 10))
        self.assertEqual(s3["questions"], [])
        self.assertEqual(s3["proposal"]["version"], 1)
        self.assertEqual(s3["version"], 3)

    def test_c02_02b_bare_answer_to_topic_question(self):
        (_, _, _), (s2, _, _) = chat("Game ôn tiếng việt lớp 3", "Từ láy và từ ghép")
        self.assertEqual(s2["requirements"]["topic"], "Từ láy và từ ghép")
        self.assertEqual(s2["status"], "awaiting_confirmation")

    def test_c02_03_full_info_at_once(self):
        st, reply, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng có nhớ, 10 câu")
        self.assertEqual(st["status"], "awaiting_confirmation")
        self.assertEqual(st["questions"], [])
        self.assertIn("Xác nhận phương án", reply)
        self.assertEqual(st["proposal"]["kind"], "plan_v2")

    def test_c02_06_list_game_not_forced_into_exam(self):
        st, reply, _ = turn("Làm vòng quay chọn tên học sinh gọi lên bảng")
        self.assertEqual(st["status"], "awaiting_confirmation")
        self.assertEqual(st["missingFields"], [])
        self.assertIsNone(st["requirements"]["subject"])
        joined = " ".join(st["proposal"]["assumptions"])
        self.assertNotIn("câu", joined.replace("Danh sách", ""))
        self.assertIsNone(st["proposal"]["exam"])

    def test_list_game_by_catalog_player(self):
        cat = {"players": [{"id": 2, "name": "Vòng quay", "manifest": {"content": {"kind": "texts"}}}]}
        r = S.normalize_requirements({"gamePreference": {"playerId": 2}})
        self.assertEqual(C.find_missing_fields(r, cat), [])
        r = S.normalize_requirements({"gamePreference": {"playerId": 1}})
        self.assertEqual(C.find_missing_fields(r, cat), ["subject", "gradeOrAudience", "topic"])

    def test_existing_exam_needs_no_topic(self):
        r = S.normalize_requirements({"contentSource": {"kind": "existing_exam", "examId": 4}})
        self.assertEqual(C.find_missing_fields(r), [])

    def test_c02_17_default_count_is_assumption_only(self):
        st, _, _ = turn("Game ôn toán lớp 2 chủ đề phép trừ")
        self.assertIsNone(st["requirements"]["questionCount"])
        self.assertIn("Số câu mặc định: 10 câu.", st["proposal"]["assumptions"])


class Edit(unittest.TestCase):
    def setUp(self):
        self.c = ctx()
        self.st, _, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng, 10 câu", context=self.c)

    def test_c02_04_edit_one_field(self):
        st, reply, _ = turn("đổi thành 15 câu", self.st, self.c)
        self.assertEqual(st["requirements"]["questionCount"], 15)
        for k in ("subject", "gradeOrAudience", "topic"):
            self.assertEqual(st["requirements"][k], self.st["requirements"][k])
        self.assertEqual(st["proposal"]["proposalId"], self.st["proposal"]["proposalId"])
        self.assertEqual(st["proposal"]["version"], 2)
        self.assertEqual(st["proposal"]["changes"], ["Số câu: 10 → 15"])
        self.assertIn("phiên bản 2", reply)

    def test_c02_05_new_request_resets(self):
        st, _, _ = turn("Yêu cầu mới: game tiếng anh lớp 5 chủ đề từ vựng màu sắc", self.st, self.c)
        req = st["requirements"]
        self.assertEqual((req["subject"], req["gradeOrAudience"], req["questionCount"]), ("Tiếng Anh", "Lớp 5", None))
        self.assertNotEqual(st["proposal"]["proposalId"], self.st["proposal"]["proposalId"])
        self.assertEqual(st["proposal"]["version"], 1)

    def test_c02_07_unmentioned_fields_kept(self):
        st, _, _ = turn("độ khó dễ thôi", self.st, self.c)
        self.assertEqual(st["requirements"]["difficulty"], "Dễ")
        self.assertEqual(st["requirements"]["topic"], "phép cộng")
        self.assertEqual(st["requirements"]["questionCount"], 10)

    def test_no_change_keeps_proposal_version(self):
        st, _, _ = turn("game này chơi thế nào?", self.st, self.c)
        self.assertEqual(st["proposal"], self.st["proposal"])
        self.assertEqual(st["version"], self.st["version"])

    def test_c02_08_typed_agree_does_not_confirm(self):
        st, reply, _ = turn("đồng ý", self.st, self.c)
        self.assertEqual(st["confirmations"], {})
        self.assertEqual(st["proposal"]["status"], "awaiting_confirmation")
        self.assertIn("bấm nút", reply)

    def test_c02_09_confirm_plan(self):
        p = self.st["proposal"]
        st, f = W.confirm_plan(self.st, p["proposalId"], 1, now=1.0)
        self.assertIsNone(f)
        self.assertEqual(st["confirmations"], {"proposalId": p["proposalId"], "version": 1, "at": 1.0, "scope": "requirements"})
        self.assertEqual(st["proposal"]["status"], "confirmed")
        self.assertNotEqual(st["status"], "ready")
        again, f = W.confirm_plan(st, p["proposalId"], 1, now=2.0)
        self.assertEqual((again, f), (st, None))  # bấm lại không đổi gì
        _, f = W.confirm_plan(self.st, p["proposalId"], 2)
        self.assertEqual(f["code"], "stale_version")
        _, f = W.confirm_plan(self.st, "p-khac", 1)
        self.assertEqual(f["code"], "invalid_input")

    def test_c02_10_edit_after_confirm_cancels_confirmation(self):
        p = self.st["proposal"]
        confirmed, _ = W.confirm_plan(self.st, p["proposalId"], 1)
        st, _, _ = turn("đổi thành 12 câu", confirmed, self.c)
        self.assertEqual(st["confirmations"], {})
        self.assertEqual((st["proposal"]["version"], st["proposal"]["status"]), (2, "awaiting_confirmation"))
        _, f = W.confirm_plan(st, p["proposalId"], 1)
        self.assertEqual(f["code"], "stale_version")

    def test_edit_that_removes_essential_drops_proposal(self):
        st, _, _ = turn("x", self.st, ctx(call_model=FakeModel({"intent": "update", "reply": "ok",
                                                                "requirementsPatch": {"topic": None}})))
        self.assertEqual(st["status"], "clarifying")
        self.assertIsNone(st["proposal"])
        self.assertEqual(st["missingFields"], ["topic"])

    def test_c02_13_stale_expected_version_no_ai_call(self):
        m = FakeModel()
        st, reply, meta = turn("đổi thành 15 câu", self.st, ctx(call_model=m), expectedVersion=self.st["version"] - 1)
        self.assertEqual(meta["failure"]["code"], "stale_version")
        self.assertEqual((m.calls, st), (0, self.st))
        st, _, meta = turn("đổi thành 15 câu", self.st, self.c, expectedVersion=self.st["version"])
        self.assertIsNone(meta["failure"])

    def test_c02_19_off_topic_no_change(self):
        st, reply, _ = turn("Thời tiết Hà Nội mai thế nào?", self.st, self.c)
        self.assertEqual(st, self.st)
        self.assertIn("game học tập", reply)


class ModelPath(unittest.TestCase):
    GOOD = {"intent": "new_request", "reply": "ok", "requirementsPatch": {"subject": "Toán", "gradeOrAudience": "Lớp 2"}}

    def test_c02_11_repair_once(self):
        m = FakeModel("không phải json", self.GOOD)
        st, _, meta = turn("Game ôn toán lớp 2", context=ctx(call_model=m))
        self.assertEqual((m.calls, meta["calls"], meta["failure"]), (2, 2, None))
        self.assertEqual(st["missingFields"], ["topic"])
        self.assertEqual((meta["simulated"], meta["model"]), (False, "mock-model"))

    def test_c02_11b_still_broken_after_repair(self):
        m = FakeModel("hỏng", "{vẫn hỏng")
        before = S.new_state()
        st, reply, meta = turn("Game ôn toán", before, ctx(call_model=m))
        self.assertEqual((m.calls, meta["failure"]["code"]), (2, "invalid_model_output"))
        self.assertEqual(st, before)
        self.assertEqual(reply, meta["failure"]["message"])

    def test_c02_12_model_exception(self):
        m = FakeModel(RuntimeError("401 bad key sk-FAKE0000000000"))
        st, reply, meta = turn("Game ôn toán", context=ctx(call_model=m))
        self.assertEqual(meta["failure"]["code"], "model_unavailable")
        self.assertTrue(meta["failure"]["retryable"])
        self.assertNotIn("sk-FAKE", reply)
        self.assertEqual(st, S.new_state())

    def test_c02_14_fake_mode_is_labeled(self):
        _, _, meta = turn("Game ôn toán")
        self.assertEqual((meta["simulated"], meta["model"], meta["calls"]), (True, "fake-rules", 0))

    def test_c02_15_model_cannot_approve(self):
        m = FakeModel(dict(self.GOOD, requirementsPatch={"subject": "Toán", "gradeOrAudience": "Lớp 2", "topic": "Cộng"},
                           status="ready", teacherApproved=True, appId=5, confirmations={"version": 1}))
        st, _, _ = turn("x", context=ctx(call_model=m))
        self.assertEqual(st["status"], "awaiting_confirmation")
        self.assertEqual(st["confirmations"], {})
        self.assertIsNone(st["result"])

    def test_model_suggested_question_text_used_only_for_missing(self):
        m = FakeModel(dict(self.GOOD, questions=[{"field": "topic", "text": "Ôn bảng cộng hay bảng trừ?"},
                                                 {"field": "subject", "text": "Môn gì?"}]))
        st, reply, _ = turn("x", context=ctx(call_model=m))
        self.assertEqual(st["questions"], [{"field": "topic", "text": "Ôn bảng cộng hay bảng trừ?"}])
        self.assertNotIn("Môn gì", reply)

    def test_prompt_contains_state_not_html(self):
        m = FakeModel(self.GOOD)
        st = S.new_state()
        st["proposal"] = {"proposalId": "p1", "version": 1, "player": {"html": "<script>SECRET_HTML</script>"}}
        turn("x", st, ctx(call_model=m, history=[{"role": "user", "text": "chào"}]))
        # system prompt cố định; user prompt có requirements + lịch sử, không có HTML của proposal
        m2 = FakeModel(self.GOOD)
        captured = {}

        def spy(system, user):
            captured["user"] = user
            return m2(system, user)
        turn("x", st, ctx(call_model=spy))
        self.assertIn("Yêu cầu hiện tại", captured["user"])
        self.assertNotIn("SECRET_HTML", captured["user"])


class Safety(unittest.TestCase):
    def test_c02_16_audio_warns_mouse_kept(self):
        st, reply, _ = turn("Game ôn toán lớp 1 chủ đề đếm số, học sinh trả lời bằng giọng nói")
        self.assertEqual(st["requirements"]["interaction"]["requestedKinds"], ["audio"])
        self.assertIs(st["requirements"]["interaction"]["mouse"], True)
        self.assertEqual(st["proposal"]["warnings"][0]["code"], "unsupported_interaction")
        self.assertIsNone(st["proposal"]["interactionModel"]["kind"])
        self.assertIn("chưa chạy được", reply)

    def test_hands_request_recorded(self):
        st, _, _ = turn("Game ôn toán lớp 2 chủ đề phép cộng, chơi bằng bàn tay")
        self.assertEqual(st["proposal"]["interactionModel"], {"modelId": None, "kind": "hands", "mapping": {}, "mouse": True})

    def test_c02_18_no_html_no_artifacts(self):
        rows = chat("Tạo game ôn toán", "lớp 2", "phép cộng, 10 câu", "đổi thành 12 câu", "đồng ý")
        for st, reply, _ in rows:
            raw = json.dumps(st, ensure_ascii=False) + reply
            for bad in ("<html", "<script", "srcdoc"):
                self.assertNotIn(bad, raw)
            self.assertIsNone(st["result"])
            self.assertNotEqual(st["status"], "ready")
            if st["proposal"]:
                self.assertIsNone(st["proposal"]["exam"])
                self.assertIsNone(st["proposal"]["interactionModel"]["modelId"])
            pub = S.to_public_reply(st, reply, True, "fake-rules")  # C01 serialize được mọi trạng thái
            json.dumps(pub, ensure_ascii=False)

    def test_input_state_not_mutated(self):
        st, _, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng, 10 câu")
        before = json.dumps(st, sort_keys=True, ensure_ascii=False)
        turn("đổi thành 15 câu", st)
        W.confirm_plan(st, st["proposal"]["proposalId"], 1)
        self.assertEqual(json.dumps(st, sort_keys=True, ensure_ascii=False), before)

    def test_merge_semantics(self):
        old = S.normalize_requirements({"topic": "Cộng", "gamePreference": {"mode": "reuse_existing", "playerId": 1}})
        new = C.merge_requirements(old, {"gamePreference": {"playerId": 2}, "questionCount": None})
        self.assertEqual(new["gamePreference"], {"mode": "reuse_existing", "playerId": 2, "description": None})
        self.assertEqual(new["topic"], "Cộng")
        self.assertEqual(old["gamePreference"]["playerId"], 1)

def dump(st):
    return json.dumps(st, sort_keys=True, ensure_ascii=False)


class CancelPlan(unittest.TestCase):
    """C02-20..26 — hủy phương án (reject_intent)."""
    REJECT = "không đồng ý, hủy phương án này"

    def setUp(self):
        self.c = ctx()
        self.st, _, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng, 10 câu", context=self.c)
        self.p = self.st["proposal"]

    def _assert_cancelled(self, st, reply, before):
        self.assertEqual(st["status"], "needs_revision")
        self.assertEqual(st["proposal"]["status"], "cancelled")
        self.assertEqual(st["proposal"]["version"], before["proposal"]["version"])
        self.assertEqual(st["confirmations"], {})
        self.assertEqual(st["version"], before["version"] + 1)
        self.assertEqual(st["requirements"], before["requirements"])
        self.assertNotIn("đã xác nhận", reply)

    def test_c02_20_cancel_before_confirm(self):
        before = dump(self.st)
        st, reply, _ = turn(self.REJECT, self.st, self.c)
        self._assert_cancelled(st, reply, self.st)
        self.assertEqual(dump(self.st), before)

    def test_c02_21_cancel_after_confirm(self):
        confirmed, _ = W.confirm_plan(self.st, self.p["proposalId"], 1)
        before = dump(confirmed)
        st, reply, _ = turn(self.REJECT, confirmed, self.c)
        self._assert_cancelled(st, reply, confirmed)
        self.assertEqual(dump(confirmed), before)

    def test_c02_22_cancel_twice_or_no_proposal_unchanged(self):
        cancelled, _, _ = turn(self.REJECT, self.st, self.c)
        again, _, _ = turn(self.REJECT, cancelled, self.c)
        self.assertEqual(again, cancelled)
        empty = S.new_state()
        st, _, _ = turn(self.REJECT, empty, self.c)
        self.assertEqual(st, empty)

    def test_c02_23_confirm_cancelled_rejected(self):
        cancelled, _, _ = turn(self.REJECT, self.st, self.c)
        before = dump(cancelled)
        st, f = W.confirm_plan(cancelled, self.p["proposalId"], 1)
        self.assertEqual(f["code"], "stale_version")
        self.assertIn("đã bị hủy", f["message"])
        self.assertEqual(dump(st), before)
        self.assertEqual(st["confirmations"], {})

    def test_c02_24_after_cancel_agree_or_no_change_stays_cancelled(self):
        cancelled, _, _ = turn(self.REJECT, self.st, self.c)
        for text in ("đồng ý", "game này chơi thế nào?"):
            st, _, _ = turn(text, cancelled, self.c)
            self.assertEqual(st["status"], "needs_revision", text)
            self.assertEqual(st["proposal"]["status"], "cancelled", text)
            self.assertEqual(st["confirmations"], {}, text)

    def test_c02_25_edit_after_cancel_needs_reconfirm(self):
        cancelled, _, _ = turn(self.REJECT, self.st, self.c)
        before = dump(cancelled)
        st, _, _ = turn("đổi thành 15 câu", cancelled, self.c)
        self.assertEqual(dump(cancelled), before)
        self.assertEqual(st["status"], "awaiting_confirmation")
        self.assertEqual(st["proposal"]["proposalId"], self.p["proposalId"])
        self.assertEqual(st["proposal"]["version"], cancelled["proposal"]["version"] + 1)
        self.assertIn("Số câu: 10 → 15", st["proposal"]["changes"])
        self.assertEqual(st["confirmations"], {})
        _, f = W.confirm_plan(st, self.p["proposalId"], cancelled["proposal"]["version"])
        self.assertEqual(f["code"], "stale_version")
        ok, f = W.confirm_plan(st, self.p["proposalId"], st["proposal"]["version"])
        self.assertIsNone(f)
        self.assertEqual(ok["proposal"]["status"], "confirmed")

    def test_c02_26_new_request_after_cancel(self):
        cancelled, _, _ = turn(self.REJECT, self.st, self.c)
        st, _, _ = turn("Yêu cầu mới: game tiếng anh lớp 5 chủ đề từ vựng màu sắc", cancelled, self.c)
        self.assertNotEqual(st["proposal"]["proposalId"], self.p["proposalId"])
        self.assertEqual(st["proposal"]["version"], 1)


class MouseOnly(unittest.TestCase):
    def test_c02_27_hands_mouse_only_hands_again(self):
        c = ctx()
        s1, _, _ = turn("Game ôn toán lớp 2 chủ đề phép cộng, chơi bằng bàn tay", context=c)
        self.assertEqual(s1["proposal"]["interactionModel"]["kind"], "hands")
        conf, _ = W.confirm_plan(s1, s1["proposal"]["proposalId"], 1)
        b1 = dump(conf)
        s2, _, _ = turn("không dùng camera, chỉ dùng chuột", conf, c)
        self.assertEqual(dump(conf), b1)
        self.assertEqual(s2["proposal"]["version"], 2)
        self.assertEqual(s2["proposal"]["interactionModel"], {"modelId": None, "kind": None, "mapping": {}, "mouse": True})
        self.assertEqual(s2["confirmations"], {})
        self.assertIn("Chỉ chơi bằng chuột, không dùng camera.", s2["proposal"]["assumptions"])
        self.assertIs(s2["requirements"]["interaction"]["useModel"], False)
        b2 = dump(s2)
        s3, _, _ = turn("chơi bằng bàn tay", s2, c)
        self.assertEqual(dump(s2), b2)
        self.assertEqual(s3["proposal"]["version"], 3)
        self.assertEqual(s3["proposal"]["interactionModel"]["kind"], "hands")
        self.assertEqual(s3["status"], "awaiting_confirmation")
        self.assertEqual(s3["confirmations"], {})

    def test_c02_28_mouse_only_no_audio_warning(self):
        r = S.normalize_requirements({"subject": "Toán", "gradeOrAudience": "Lớp 2", "topic": "cộng",
                                      "interaction": {"requestedKinds": ["audio"], "useModel": False}})
        p = W._build_proposal(None, r, None, ids(), [])
        self.assertEqual(p["warnings"], [])


class GameKind(unittest.TestCase):
    def kind(self, req, cat=None):
        return C.game_kind(S.normalize_requirements(req), cat)

    def test_c02_29_wheel_quiz_missing_topic_asks_topic(self):
        c = ctx()
        s1, _, _ = turn("Tạo vòng quay câu hỏi trắc nghiệm toán lớp 2, 10 câu", context=c)
        self.assertEqual(s1["status"], "clarifying")
        self.assertEqual(s1["missingFields"], ["topic"])
        s2, _, _ = turn("phép cộng", s1, c)
        self.assertEqual(s2["status"], "awaiting_confirmation")
        self.assertTrue(s2["proposal"]["reason"].startswith("Game ôn tập"))

    def test_c02_30_wheel_pick_names_not_exam(self):
        st, _, _ = turn("Làm vòng quay chọn tên học sinh gọi lên bảng")
        self.assertEqual((st["status"], st["missingFields"]), ("awaiting_confirmation", []))
        self.assertIsNone(st["requirements"]["subject"])

    def test_c02_31_bare_wheel_asks_preference(self):
        c = ctx()
        s1, _, _ = turn("Tạo vòng quay", context=c)
        self.assertEqual(s1["status"], "clarifying")
        self.assertEqual(s1["missingFields"], ["gamePreference"])
        self.assertEqual([q["text"] for q in s1["questions"]], [C.FIELD_QUESTIONS["gamePreference"]])
        s2, _, _ = turn("quay câu hỏi", s1, c)
        self.assertEqual(s2["status"], "clarifying")
        self.assertEqual(s2["missingFields"], ["subject", "gradeOrAudience", "topic"])
        s3, _, _ = turn("chọn tên học sinh", s1, c)
        self.assertEqual((s3["status"], s3["missingFields"]), ("awaiting_confirmation", []))

    def test_c02_32_catalog_manifest_decides(self):
        cat = {"players": [{"id": 7, "name": "A", "manifest": {"content": {"kind": "texts"}}},
                           {"id": 8, "name": "B", "manifest": {"questions": "exam"}}]}
        self.assertEqual(self.kind({"gamePreference": {"playerId": 7, "description": "vòng quay câu hỏi"}}, cat), "list")
        self.assertEqual(self.kind({"gamePreference": {"playerId": 8, "description": "chọn tên học sinh"}}, cat), "questions")

    def test_c02_33_signal_priority(self):
        # Review lần 2: mô tả có tín hiệu danh sách thắng subject cũ (không còn "có subject thì luôn là câu hỏi").
        self.assertEqual(self.kind({"subject": "Toán", "gamePreference": {"description": "chọn tên"}}), "list")
        self.assertEqual(self.kind({"gamePreference": {"description": "bốc thăm gọi tên"}}), "list")
        self.assertIsNone(self.kind({"gamePreference": {"description": "vòng quay"}}))
        self.assertEqual(self.kind({}), "questions")
        self.assertEqual(self.kind({"contentSource": {"kind": "existing_exam", "examId": 4}}), "questions")


class TopicKeep(unittest.TestCase):
    """C02-34 — TOPIC_CUT không cắt ở chữ "có"; giữ/đổi chủ đề."""

    def topic(self, text):
        return C.fake_analyze(text, S.new_state())["requirementsPatch"]["topic"]

    def test_c02_34_topic_cut(self):
        cases = {
            "Game ôn toán lớp 2 chủ đề phép cộng có nhớ, 10 câu": "phép cộng có nhớ",
            "Game ôn toán lớp 2 chủ đề phép cộng không nhớ": "phép cộng không nhớ",
            "phép cộng có nhớ trong phạm vi 100, 10 câu, chơi bằng bàn tay": "phép cộng có nhớ trong phạm vi 100",
            "Game ôn toán lớp 2 chủ đề phép cộng có nhớ có 10 câu": "phép cộng có nhớ",
            "phép chia có dư chỉ dùng chuột": "phép chia có dư",
            "chủ đề so sánh bằng nhau cho lớp 1": "so sánh bằng nhau",  # không "chủ đề" thì không nhận topic
        }
        for text, want in cases.items():
            self.assertEqual(self.topic(text), want, text)

    def test_c02_35_explicit_topic_change(self):
        c = ctx()
        s1, _, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng, 10 câu", context=c)
        b = dump(s1)
        s2, _, _ = turn("chủ đề phép trừ có nhớ", s1, c)
        self.assertEqual(dump(s1), b)
        self.assertEqual(s2["requirements"]["topic"], "phép trừ có nhớ")

    def test_c02_36_bare_topic_answer(self):
        (_, _, _), (s2, _, _) = chat("Game ôn tiếng việt lớp 3", "Từ láy và từ ghép")
        self.assertEqual(s2["requirements"]["topic"], "Từ láy và từ ghép")


class GameSwitch(unittest.TestCase):
    """C02-37.. — đổi loại game chỉ khi có cụm đổi tường minh."""

    def test_c02_37_switch_to_list_and_back(self):
        c = ctx()
        s1, _, _ = turn("Tạo game ôn toán lớp 2", context=c)
        b1 = dump(s1)
        s2, _, _ = turn("Đổi sang vòng quay chọn tên học sinh", s1, c)
        self.assertEqual(dump(s1), b1)
        self.assertEqual(s2["status"], "awaiting_confirmation")
        self.assertEqual(s2["missingFields"], [])
        self.assertEqual(C.game_kind(s2["requirements"], None), "list")
        self.assertEqual(s2["requirements"]["subject"], "Toán")
        self.assertEqual(s2["requirements"]["gradeOrAudience"], "Lớp 2")
        self.assertTrue(s2["proposal"]["reason"].startswith("Game danh sách"))
        b2 = dump(s2)
        s3, _, _ = turn("thôi, quay câu hỏi phép cộng", s2, c)
        self.assertEqual(dump(s2), b2)
        self.assertEqual(C.game_kind(s3["requirements"], None), "questions")
        self.assertEqual(s3["requirements"]["topic"], "phép cộng")
        self.assertEqual(s3["status"], "awaiting_confirmation")

    def test_c02_38_no_switch_phrase_keeps_questions(self):
        c = ctx()
        s1, _, _ = turn("Game trắc nghiệm toán lớp 2 chủ đề phép cộng, 10 câu", context=c)
        b = dump(s1)
        s2, _, _ = turn("lấy từ danh sách từ vựng bài 5", s1, c)
        self.assertEqual(dump(s1), b)
        self.assertEqual(C.game_kind(s2["requirements"], None), "questions")
        self.assertEqual(s2["requirements"]["topic"], "phép cộng")

    def test_c02_39_english_animals_then_switch(self):
        c = ctx()
        s1, _, _ = turn("Game ôn tiếng anh lớp 3 chủ đề động vật", context=c)
        s2, _, _ = turn("gọi tên các con vật bằng tiếng anh", s1, c)
        self.assertEqual(C.game_kind(s2["requirements"], None), "questions")
        self.assertEqual(s2["requirements"]["topic"], "động vật")
        b = dump(s2)
        s3, _, _ = turn("chuyển sang bốc thăm gọi tên học sinh", s2, c)
        self.assertEqual(dump(s2), b)
        self.assertEqual(C.game_kind(s3["requirements"], None), "list")

    def test_c02_40_list_phrase_without_switch_ignored(self):
        c = ctx()
        s1, _, _ = turn("Tạo game ôn toán lớp 2", context=c)
        b = dump(s1)
        s2, _, _ = turn("vòng quay chọn tên học sinh", s1, c)
        self.assertEqual(dump(s1), b)
        self.assertEqual(dump(s2), b)
        self.assertEqual((s2["status"], s2["missingFields"]), ("clarifying", ["topic"]))
        s3, _, _ = turn("Đổi sang vòng quay chọn tên học sinh", s2, c)
        self.assertEqual((s3["status"], s3["missingFields"]), ("awaiting_confirmation", []))

    def test_c02_41_list_game_ignores_extra_question_phrase(self):
        c = ctx()
        s1, _, _ = turn("Làm vòng quay chọn tên học sinh gọi lên bảng", context=c)
        s2, _, _ = turn("thêm câu hỏi phụ cho vui", s1, c)
        self.assertEqual(C.game_kind(s2["requirements"], None), "list")


class GameConflict(unittest.TestCase):
    """C02-42 — Player đã chọn mâu thuẫn loại game mới."""
    CAT = {"players": [{"id": 8, "name": "Quiz", "manifest": {"questions": "exam"}}]}

    def setUp(self):
        self.c = ctx(catalog=self.CAT)
        m = FakeModel({"intent": "new_request", "reply": "ok",
                       "requirementsPatch": {"subject": "Toán", "gradeOrAudience": "Lớp 2", "topic": "phép cộng",
                                             "gamePreference": {"playerId": 8}}})
        self.s0, _, _ = turn("x", context=ctx(catalog=self.CAT, call_model=m))
        self.assertEqual(self.s0["requirements"]["gamePreference"]["playerId"], 8)
        self.s1, _, _ = turn("Đổi sang vòng quay chọn tên học sinh", self.s0, self.c)

    def test_c02_42_conflict_asked(self):
        s1 = self.s1
        self.assertEqual(s1["status"], "clarifying")
        self.assertEqual(s1["missingFields"], ["gameConflict"])
        self.assertEqual(s1["requirements"]["gamePreference"]["playerId"], 8)
        self.assertEqual([q["text"] for q in s1["questions"]], [C.FIELD_QUESTIONS["gameConflict"]])

    def test_c02_43_choose_other_game(self):
        b = dump(self.s1)
        s2, _, _ = turn("chọn game khác", self.s1, self.c)
        self.assertEqual(dump(self.s1), b)
        r = s2["requirements"]
        self.assertIsNone(r["gamePreference"]["playerId"])
        self.assertEqual(C.game_kind(r, self.CAT), "list")
        self.assertEqual(s2["status"], "awaiting_confirmation")
        self.assertEqual((r["subject"], r["gradeOrAudience"], r["topic"]), ("Toán", "Lớp 2", "phép cộng"))

    def test_c02_44_keep_chosen_game(self):
        b = dump(self.s1)
        s2, _, _ = turn("giữ game đã chọn", self.s1, self.c)
        self.assertEqual(dump(self.s1), b)
        g = s2["requirements"]["gamePreference"]
        self.assertIsNone(g["description"])
        self.assertEqual(g["playerId"], 8)
        self.assertEqual(C.game_kind(s2["requirements"], self.CAT), "questions")
        self.assertEqual(s2["status"], "awaiting_confirmation")


if __name__ == "__main__":
    unittest.main()
