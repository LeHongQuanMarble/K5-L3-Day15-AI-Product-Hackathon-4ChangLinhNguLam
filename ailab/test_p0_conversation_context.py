"""Regression Tests TC01–TC12 — P0 Conversation Context, Multi-turn Requirements & Grounded Resource Selection.

100% offline (fixtures + mock call_model, isolated temp SQLite DB). Không gọi API trả phí, không chạm runtime DB.
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "codebase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402
import agent_bridge  # noqa: E402
import conversation_state as cs  # noqa: E402
import llm as ailab_llm  # noqa: E402
import contract  # noqa: E402


def _make_player(pid, name, kinds, inputs, questions="exam", status="approved"):
    man = {
        "name": name,
        "description": "Trò chơi %s" % name,
        "questions": questions,
        "kinds": kinds,
        "inputs": inputs,
    }
    return {"id": pid, "name": name, "manifest": man, "status": status}


def _make_model(mid, name, kind, keys=("A", "B", "C", "D"), status="ready", ready=True, url="https://tm.local/m1/"):
    outs = [{"key": k, "role": "action"} for k in keys] + [{"key": "none", "role": "empty"}]
    return {"id": mid, "name": name, "kind": kind, "outputs": outs, "status": status, "ready": ready, "url": url}


def _quiz_html(title="Bản nháp mới"):
    return ailab_llm.QUIZ_TEMPLATE.replace("__TITLE__", title)


def _temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c, path


class TestP0ConversationContext(unittest.TestCase):
    def setUp(self):
        self.img_model = _make_model(10, "Nhận diện thẻ A-D", "image", ("A", "B", "C", "D"))
        self.hands_model = _make_model(1, "Bàn tay (MediaPipe)", "hands", ("fist", "open"))
        self.audio_model = _make_model(20, "Âm thanh A B C D", "audio", ("A", "B", "C", "D"))
        self.broken_img_model = _make_model(11, "Ảnh lỗi 404", "image", ("A", "B"), status="broken", ready=False, url="https://cdn.local/models/x/model.json")

        self.quiz_img_player = _make_player(
            1, "Quiz ABCD bằng cử chỉ", ["image", "pose"],
            [{"key": k, "required": True, "accepts": ["action"]} for k in "ABCD"],
        )
        self.hands_only_player = _make_player(
            6, "Tết 2027: Dê Vàng và cổng băng", ["hands"],
            [{"key": "grab", "required": True, "accepts": ["action"]}, {"key": "release", "required": False, "accepts": ["action"]}],
        )
        self.audio_player = _make_player(
            5, "Giải cứu thế giới", ["image", "pose", "audio"],
            [{"key": k, "required": True, "accepts": ["action"]} for k in "ABCD"],
        )
        self.sample_exam = {
            "id": 1,
            "name": "Toán lớp 3 — Phép nhân",
            "content": "2 x 3 = ? | 5 | 6 | 7 | 8 | =B\n3 x 4 = ? | 10 | 11 | 12 | 13 | =C",
        }
        self.registry = {
            "players": [self.quiz_img_player, self.hands_only_player, self.audio_player],
            "models": [self.hands_model, self.img_model, self.audio_model],
            "exams": [self.sample_exam],
        }

    # TC01 — Multi-turn information collection
    def test_tc01_multiturn_information_collection(self):
        st = cs.new_state(conversation_id=101, user_id=7)
        st, _ = cs.update_state_from_turn(st, "Tạo game Toán lớp 3.", self.registry)
        self.assertEqual(st["learning_subject"], "Toán")
        self.assertEqual(st["grade_level"], "Lớp 3")
        self.assertIn("preferred_model_kind", st["missing_requirements"])

        st, _ = cs.update_state_from_turn(st, "Phép nhân.", self.registry)
        self.assertEqual(st["learning_subject"], "Toán")
        self.assertEqual(st["grade_level"], "Lớp 3")
        self.assertEqual(st["learning_topic"], "Phép nhân")

        st, _ = cs.update_state_from_turn(st, "10 câu hỏi.", self.registry)
        self.assertEqual(st["question_count"], 10)
        self.assertEqual(st["learning_topic"], "Phép nhân")

        st, _ = cs.update_state_from_turn(st, "Model hình ảnh.", self.registry)
        self.assertEqual(st["learning_subject"], "Toán")
        self.assertEqual(st["grade_level"], "Lớp 3")
        self.assertEqual(st["learning_topic"], "Phép nhân")
        self.assertEqual(st["question_count"], 10)
        self.assertEqual(st["preferred_model_kind"], "image")
        self.assertEqual(st["missing_requirements"], [])

    # TC02 — Explicit Model selection
    def test_tc02_explicit_model_selection(self):
        st = cs.new_state(conversation_id=102, user_id=7)
        st, _ = cs.update_state_from_turn(
            st, "Tạo game Toán lớp 3 phép nhân", self.registry,
            request_hints={"selected_model_id": 10},
        )
        mres = cs.resolve_grounded_model(st, self.registry, explicit_model_id=10)
        self.assertEqual(mres["status"], "selected")
        self.assertEqual(mres["model"]["id"], 10)

    # TC03 — Incompatible Player (Catalog only has hands-only player for image model)
    def test_tc03_incompatible_player_never_reused(self):
        reg = {
            "players": [self.hands_only_player],
            "models": [self.img_model],
            "exams": [self.sample_exam],
        }
        st = cs.new_state(conversation_id=103, user_id=7)
        st, _ = cs.update_state_from_turn(st, "Tạo game Toán lớp 3 dùng Model hình ảnh", reg)
        mres = cs.resolve_grounded_model(st, reg)
        self.assertEqual(mres["status"], "selected")
        self.assertEqual(mres["model"]["id"], 10)

        # Không được REUSE hands_only_player (#6) cho model image (#10)
        pres = cs.resolve_grounded_player(st, mres["model"], reg)
        self.assertEqual(pres["action"], "GENERATE")
        self.assertIsNone(pres["player"])

        # Ngay cả khi LLM router đề xuất REUSE sai -> agent.run_agent_with_state ép sang GENERATE
        routing_reply = json.dumps({
            "decision": "REUSE",
            "message": "Dùng lại Tết 2027",
            "app_name": "Game Toán hình ảnh",
            "player_id": 6,
            "model_id": 10,
            "exam_mode": "reuse_existing",
            "exam_id": 1,
        })
        gen_html = "```html\n" + _quiz_html("Game Toán hình ảnh") + "\n```"
        calls = [
            {"text": routing_reply, "model": "mock", "tokens_in": 10, "tokens_out": 10},
            {"text": "Bản nháp mới\n\n" + gen_html, "model": "mock", "tokens_in": 10, "tokens_out": 20},
        ]
        with mock.patch.object(agent, "call_model", side_effect=calls):
            env, _ = agent.run_agent_with_state(
                {"message": "Tạo game Toán lớp 3 dùng Model hình ảnh", "conversation_id": 103, "conversation_state": st, "selected_exam_id": 1},
                registry=reg,
            )
        self.assertEqual(env["decision"], "GENERATE")
        self.assertEqual(env["application_plan"]["player"]["mode"], "generate_new")

    # TC04 — Missing Model (image requested, only hands or broken image available)
    def test_tc04_missing_model_honest_clarify_no_silent_swap(self):
        reg = {
            "players": [self.quiz_img_player, self.hands_only_player],
            "models": [self.hands_model, self.broken_img_model],
            "exams": [self.sample_exam],
        }
        st = cs.new_state(conversation_id=104, user_id=7)
        with mock.patch.object(agent, "call_model") as mocked_llm:
            env, out_st = agent.run_agent_with_state(
                {"message": "Tạo game Toán lớp 3 dùng Model hình ảnh", "conversation_id": 104, "conversation_state": st},
                registry=reg,
            )
        mocked_llm.assert_not_called()  # Chặn tất định trước LLM, 0 token
        self.assertEqual(env["decision"], "ASK_CLARIFY")
        self.assertIsNone(env["application_plan"])
        self.assertIn("Bàn tay (MediaPipe)", env["message"])
        self.assertNotEqual(out_st.get("selected_model_id"), 1)
        self.assertNotEqual(out_st.get("selected_model_id"), 11)

    # TC05 — Explicit new Player ("Tạo Player mới sử dụng Model hình ảnh")
    def test_tc05_explicit_new_player_never_reuses(self):
        st = cs.new_state(conversation_id=105, user_id=7)
        routing_reply = json.dumps({
            "decision": "REUSE",
            "message": "Dùng lại Quiz",
            "app_name": "Game mới hình ảnh",
            "player_id": 1,
            "model_id": 10,
            "exam_mode": "reuse_existing",
            "exam_id": 1,
        })
        gen_html = "```html\n" + _quiz_html("Game mới hình ảnh") + "\n```"
        calls = [
            {"text": routing_reply, "model": "mock", "tokens_in": 10, "tokens_out": 10},
            {"text": "Đã tạo player mới\n\n" + gen_html, "model": "mock", "tokens_in": 10, "tokens_out": 20},
        ]
        with mock.patch.object(agent, "call_model", side_effect=calls):
            env, out_st = agent.run_agent_with_state(
                {"message": "Tạo Player mới sử dụng Model hình ảnh", "conversation_id": 105, "conversation_state": st, "selected_exam_id": 1},
                registry=self.registry,
            )
        self.assertEqual(out_st["creation_preference"], "new")
        self.assertEqual(env["decision"], "GENERATE")
        self.assertEqual(env["application_plan"]["player"]["mode"], "generate_new")

    # TC06 — Context update (image -> audio, preserve subject/grade/topic/count, re-evaluate player)
    def test_tc06_context_update_image_to_audio(self):
        st = cs.new_state(conversation_id=106, user_id=7)
        st, _ = cs.update_state_from_turn(st, "Tạo game Toán lớp 3 chủ đề Phép nhân 10 câu hỏi dùng Model hình ảnh", self.registry)
        st["selected_model_id"] = 10
        st["selected_player_id"] = 1  # Quiz ABCD không hỗ trợ audio
        st["active_draft_id"] = 55

        st2, meta = cs.update_state_from_turn(st, "Đổi sang âm thanh", self.registry)
        self.assertEqual(st2["preferred_model_kind"], "audio")
        self.assertEqual(st2["learning_subject"], "Toán")
        self.assertEqual(st2["grade_level"], "Lớp 3")
        self.assertEqual(st2["learning_topic"], "Phép nhân")
        self.assertEqual(st2["question_count"], 10)
        self.assertIsNone(st2["selected_model_id"])  # model image cũ bị xóa
        self.assertIsNone(st2["selected_player_id"])  # player không hỗ trợ audio bị xóa
        self.assertTrue(meta["invalidated_draft"])
        self.assertIsNone(st2["active_draft_id"])

        with mock.patch.object(cs.chatbot_catalog, "AUDIO_SUPPORTED", True), \
             mock.patch.object(cs.chatbot_catalog, "RUNTIME_KINDS", frozenset(("image", "pose", "hands", "audio"))):
            mres = cs.resolve_grounded_model(st2, self.registry)
            self.assertEqual(mres["status"], "selected")
            self.assertEqual(mres["model"]["id"], 20)
            pres = cs.resolve_grounded_player(st2, mres["model"], self.registry)
            self.assertEqual(pres["action"], "REUSE")
            self.assertEqual(pres["player"]["id"], 5)  # Giải cứu thế giới hỗ trợ audio

    # TC07 — Reload conversation from isolated SQLite DB
    def test_tc07_reload_conversation_restores_history_and_state(self):
        c, path = _temp_db()
        try:
            u1 = {"id": 1, "username": "gv1", "role": "user"}
            conv = agent_bridge.create_conversation(c, u1, title="Toán lớp 3")
            cid = conv["conversation_id"]
            st, _ = cs.update_state_from_turn(conv["conversation_state"], "Tạo game Toán lớp 3 chủ đề Phép nhân 10 câu", self.registry)
            agent_bridge.save_conversation_turn(
                c, cid, u1, "Tạo game Toán lớp 3 chủ đề Phép nhân 10 câu",
                {"decision": "ASK_CLARIFY", "status": "needs_clarification", "message": "Bạn muốn dùng hình thức tương tác nào?"},
                st,
            )
            reloaded = agent_bridge.get_conversation(c, cid, u1)
            self.assertEqual(reloaded["conversation_id"], cid)
            self.assertEqual(len(reloaded["messages"]), 2)
            self.assertEqual(reloaded["conversation_state"]["learning_subject"], "Toán")
            self.assertEqual(reloaded["conversation_state"]["grade_level"], "Lớp 3")
            self.assertEqual(reloaded["conversation_state"]["learning_topic"], "Phép nhân")
            self.assertEqual(reloaded["conversation_state"]["question_count"], 10)
        finally:
            c.close()
            os.remove(path)

    # TC08 — New conversation isolation
    def test_tc08_new_conversation_isolation(self):
        c, path = _temp_db()
        try:
            u1 = {"id": 1, "username": "gv1", "role": "user"}
            c1 = agent_bridge.create_conversation(c, u1, title="Cuộc 1")
            st1, _ = cs.update_state_from_turn(c1["conversation_state"], "Tạo game Toán lớp 3 10 câu dùng Model hình ảnh", self.registry)
            agent_bridge.save_conversation_turn(c, c1["conversation_id"], u1, "Tạo game Toán lớp 3", {"message": "ok"}, st1)

            c2 = agent_bridge.create_conversation(c, u1, title="Cuộc 2")
            self.assertNotEqual(c1["conversation_id"], c2["conversation_id"])
            self.assertIsNone(c2["conversation_state"]["learning_subject"])
            self.assertIsNone(c2["conversation_state"]["question_count"])
            self.assertIsNone(c2["conversation_state"]["preferred_model_kind"])
            self.assertEqual(c2["messages"], [])
        finally:
            c.close()
            os.remove(path)

    # TC09 — User isolation
    def test_tc09_user_isolation(self):
        c, path = _temp_db()
        try:
            u1 = {"id": 1, "username": "gv1", "role": "user"}
            u2 = {"id": 2, "username": "gv2", "role": "user"}
            c1 = agent_bridge.create_conversation(c, u1, title="Riêng tư của gv1")
            with self.assertRaises(agent_bridge.BridgeError) as ctx:
                agent_bridge.get_conversation(c, c1["conversation_id"], u2)
            self.assertEqual(ctx.exception.status, 404)
            self.assertEqual(agent_bridge.list_conversations(c, u2), [])
        finally:
            c.close()
            os.remove(path)

    # TC10 — Draft integrity on requirement change
    def test_tc10_draft_integrity_invalidates_old_approval(self):
        c, path = _temp_db()
        try:
            u1 = {"id": 1, "username": "gv1", "role": "user"}
            conv = agent_bridge.create_conversation(c, u1, title="Draft test")
            cid = conv["conversation_id"]
            env1 = {
                "schema_version": "1.0", "simulated": True, "decision": "REUSE", "status": "pending_approval",
                "message": "Bản nháp 1",
                "application_plan": {
                    "name": "Game 1", "player": {"mode": "reuse_existing", "player_id": 1, "html": None},
                    "model": {"model_id": 10, "kind": "image", "mapping": {"A": "A", "B": "B", "C": "C", "D": "D"}, "sure": 0.8, "hold_ms": 800},
                    "exam": {"mode": "reuse_existing", "exam_id": 1, "content": self.sample_exam["content"]},
                    "interaction": {"primary": "image", "fallback": "mouse", "mouse_always_enabled": True},
                },
                "errors": [], "warnings": [],
            }
            d1 = agent_bridge.save_draft(c, u1, env1)
            st1, _ = cs.update_state_from_turn(conv["conversation_state"], "Tạo game Toán lớp 3 dùng Model hình ảnh", self.registry)
            st1 = agent_bridge.save_conversation_turn(c, cid, u1, "Tạo game Toán lớp 3 dùng Model hình ảnh", env1, st1, active_draft_id=d1["draft_id"], active_plan_hash=d1["plan_hash"])
            self.assertEqual(st1["active_draft_id"], d1["draft_id"])

            # Thay đổi yêu cầu -> draft cũ bị vô hiệu hóa
            st2, meta = cs.update_state_from_turn(st1, "Đổi sang 15 câu hỏi", self.registry)
            self.assertTrue(meta["invalidated_draft"])
            self.assertIsNone(st2["active_draft_id"])
            self.assertIsNone(st2["active_plan_hash"])

            env2 = json.loads(json.dumps(env1))
            env2["application_plan"]["name"] = "Game 2 (15 câu)"
            d2 = agent_bridge.save_draft(c, u1, env2)
            self.assertNotEqual(d1["draft_id"], d2["draft_id"])
            self.assertNotEqual(d1["plan_hash"], d2["plan_hash"])
            # Review với approval của d1 đối chiếu env2 -> tự quay về draft
            rev = agent_bridge.review({"envelope": env2}, {"status": "approved", "plan_hash": d1["plan_hash"]})
            self.assertEqual(rev["status"], "draft")
            self.assertFalse(rev["can_publish"])
        finally:
            c.close()
            os.remove(path)

    # TC11 — Catalog grounding (non-existent / unauthorized Model ID or Player ID)
    def test_tc11_catalog_grounding_rejects_unknown_ids(self):
        st = cs.new_state(conversation_id=111, user_id=7)
        with mock.patch.object(agent, "call_model") as mocked_llm:
            env_m, _ = agent.run_agent_with_state(
                {"message": "Tạo game Toán lớp 3", "conversation_id": 111, "conversation_state": st, "selected_model_id": 9999},
                registry=self.registry,
            )
            env_p, _ = agent.run_agent_with_state(
                {"message": "Tạo game Toán lớp 3", "conversation_id": 111, "conversation_state": st, "selected_player_id": 8888},
                registry=self.registry,
            )
        mocked_llm.assert_not_called()
        self.assertEqual(env_m["decision"], "ERROR")
        self.assertEqual(env_p["decision"], "ERROR")
        self.assertIsNone(env_m["application_plan"])
        self.assertIsNone(env_p["application_plan"])

    # TC12 — No unnecessary clarification when full requirements provided upfront
    def test_tc12_no_unnecessary_clarification_when_complete(self):
        st = cs.new_state(conversation_id=112, user_id=7)
        captured_prompts = []

        def fake_llm(sys_p, user_p):
            captured_prompts.append(user_p)
            return {
                "text": json.dumps({
                    "decision": "REUSE",
                    "message": "Đã ghép Quiz ABCD với Model hình ảnh.",
                    "app_name": "Toán 3 Phép nhân",
                    "player_id": 1,
                    "model_id": 10,
                    "mapping": {"A": "A", "B": "B", "C": "C", "D": "D"},
                    "exam_mode": "reuse_existing",
                    "exam_id": 1,
                }),
                "model": "mock", "tokens_in": 10, "tokens_out": 10,
            }

        with mock.patch.object(agent, "call_model", side_effect=fake_llm):
            env, out_st = agent.run_agent_with_state(
                {
                    "message": "Tạo game Toán lớp 3 chủ đề Phép nhân gồm 5 câu hỏi bằng Model hình ảnh",
                    "conversation_id": 112,
                    "conversation_state": st,
                    "selected_exam_id": 1,
                },
                registry=self.registry,
            )
        self.assertEqual(out_st["missing_requirements"], [])
        self.assertIn("ĐÃ ĐỦ yêu cầu cốt lõi", captured_prompts[0])
        self.assertEqual(env["decision"], "REUSE")
        self.assertEqual(env["application_plan"]["model"]["model_id"], 10)
        self.assertEqual(env["application_plan"]["player"]["player_id"], 1)

    def test_tc13_multiturn_short_hands_reply_rescues_info_into_compatible_reuse(self):
        """Regression live UAT: 'tạo game toán lớp 3' -> 'phép nhân, model hình ảnh' -> 'bàn tay'."""
        reg = {
            "players": [self.quiz_img_player, self.hands_only_player],
            "models": [self.hands_model],
            "exams": [self.sample_exam],
        }
        st = cs.new_state(conversation_id=113, user_id=7)
        st, _ = cs.update_state_from_turn(st, "tạo game toán lớp 3", reg)
        env2, st = agent.run_agent_with_state(
            {"message": "phép nhân, model hình ảnh", "conversation_id": 113, "conversation_state": st},
            registry=reg,
        )
        self.assertEqual(env2["decision"], "ASK_CLARIFY")
        self.assertIn("Bàn tay (MediaPipe)", env2["message"])

        # Lượt 3: user chỉ gõ ngắn 'bàn tay', LLM giả lập lỡ trả INFO nhầm lẫn -> hệ thống rescue sang REUSE player #6 + tạo câu hỏi
        calls = [
            {"text": json.dumps({"decision": "INFO", "message": "Player không hỗ trợ hands"}), "model": "mock", "tokens_in": 10, "tokens_out": 10},
            {"text": "2 x 3 = ? | 5 | 6 | 7 | 8 | =B\n3 x 5 = ? | 12 | 15 | 18 | 20 | =B", "model": "mock", "tokens_in": 10, "tokens_out": 20},
        ]
        with mock.patch.object(agent, "call_model", side_effect=calls):
            env3, st3 = agent.run_agent_with_state(
                {"message": "bàn tay", "conversation_id": 113, "conversation_state": st},
                registry=reg,
            )
        self.assertEqual(env3["decision"], "REUSE")
        self.assertEqual(env3["application_plan"]["model"]["model_id"], 1)
        self.assertEqual(env3["application_plan"]["player"]["player_id"], 6)
        self.assertEqual(st3["learning_subject"], "Toán")
        self.assertEqual(st3["grade_level"], "Lớp 3")


if __name__ == "__main__":
    unittest.main()
