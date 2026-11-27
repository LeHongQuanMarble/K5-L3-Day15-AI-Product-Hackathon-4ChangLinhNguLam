"""T10 — kiểm các cụm bắt buộc sau Run 1 (mock call_model, không tốn token, không sửa benchmark)."""
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from test_t08_t09_agent_guardrails import TempCatalogTestCase, _fake_llm_reply  # noqa: E402
import agent  # noqa: E402


def run(user, payload):
    with mock.patch.object(agent, "call_model", return_value=_fake_llm_reply(payload)):
        return agent.run_agent(user)


class TestFinalize(TempCatalogTestCase):
    def test_info_reply_gets_catalog_names_draft_and_approver(self):
        env = run("Lớp Mầm non, không có camera thì chơi bằng chuột, có giọng nói không?",
                  {"decision": "INFO", "message": "Cô có thể dùng chơi bằng chuột."})
        m = env["message"]
        self.assertIn("Bàn tay (MediaPipe)", m)
        self.assertIn("DRAFT", m)
        self.assertIn("không tự duyệt", m)
        self.assertRegex(m, "chưa được Runtime hỗ trợ")
        self.assertNotIn("```", m)

    def test_ask_clarify_keeps_single_question_and_gets_draft_only(self):
        env = run("Làm game giúp tôi", {"decision": "ASK_CLARIFY", "message": "Bạn dạy môn gì"})
        m = env["message"]
        self.assertEqual(m.count("?"), 1)
        self.assertIn("DRAFT", m)
        self.assertNotIn("Bàn tay (MediaPipe)", m)

    def test_refuse_untouched(self):
        env = run("Làm game giúp tôi", {"decision": "REFUSE", "message": "Từ chối."})
        self.assertEqual(env["message"], "Từ chối.")

    def test_existing_phrases_not_duplicated(self):
        msg = ("Quiz ABCD bằng cử chỉ chơi bằng chuột. Bản nháp DRAFT chờ giáo viên duyệt; "
               "giáo viên là người duyệt cuối.")
        env = run("Ôn Toán", {"decision": "INFO", "message": msg})
        self.assertEqual(env["message"], msg)

    def test_prompt_no_longer_forces_clarify_on_fallback_input(self):
        self.assertIn("KHÔNG hỏi lại nếu đầu vào đã nêu", agent.ROUTING_SYSTEM_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
