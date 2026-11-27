"""T14 — test cầu nối Shared Core & cổng HITL (không gọi API, không ghi DB).

Chạy: python -m unittest discover -s ailab -p "test_*.py"
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "codebase"))

import agent_bridge  # noqa: E402
import ai  # noqa: E402


def plan():
    return {
        "name": "Ôn Toán",
        "player": {"mode": "reuse_existing", "player_id": 1, "html": None},
        "model": None,
        "exam": {"mode": "reuse_existing", "exam_id": 1,
                 "content": "1 + 1 bằng bao nhiêu? | 1 | 2 | =B\n2 + 2 bằng bao nhiêu? | 3 | 4 | =B"},
        "interaction": {"primary": "mouse", "fallback": "mouse", "mouse_always_enabled": True},
    }


def envelope(status="pending_approval", decision="REUSE", warnings=None):
    return {"schema_version": "1.0", "simulated": False, "decision": decision, "status": status,
            "message": "Bản nháp chờ giáo viên duyệt.", "application_plan": plan(),
            "errors": [], "warnings": warnings or []}


class ProviderMapping(unittest.TestCase):
    def test_rate_limit_and_timeout_are_503(self):
        for kind in ("rate_limit", "timeout", "network"):
            err = agent_bridge.provider_error(ai.ProviderError("openai", kind))
            self.assertEqual(err.status, 503, kind)
            self.assertNotIn("API_KEY", err.msg)

    def test_auth_config_bad_response_are_502(self):
        for kind in ("auth", "config", "bad_response", "usage_missing"):
            err = agent_bridge.provider_error(ai.ProviderError("openai", kind))
            self.assertEqual(err.status, 502, kind)

    def test_http_429_is_503(self):
        err = agent_bridge.provider_error(ai.ProviderError("openai", "http", status=429))
        self.assertEqual(err.status, 503)


class HitlGate(unittest.TestCase):
    user = {"username": "teacher1", "role": "teacher"}

    def test_publish_requires_explicit_teacher_approval(self):
        with self.assertRaises(agent_bridge.BridgeError) as ctx:
            agent_bridge.publish({"envelope": envelope()}, self.user)
        self.assertEqual(ctx.exception.status, 403)
        self.assertEqual(ctx.exception.code, "hitl_required")

    def test_publish_rejects_ai_sent_approved_status(self):
        with self.assertRaises(agent_bridge.BridgeError) as ctx:
            agent_bridge.publish({"envelope": envelope(status="APPROVED"), "approved": True}, self.user)
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.code, "hitl_forbidden")

    def test_publish_rejects_draft_and_refusal(self):
        for status, decision in (("draft", "REUSE"), ("rejected", "REUSE"),
                                 ("error", "REFUSE"), ("needs_clarification", "ASK_CLARIFY")):
            with self.assertRaises(agent_bridge.BridgeError) as ctx:
                agent_bridge.publish({"envelope": envelope(status, decision), "approved": True}, self.user)
            self.assertEqual(ctx.exception.status, 403)

    def test_publish_accepts_valid_approved_plan(self):
        out = agent_bridge.publish({"envelope": envelope(), "approved": True}, self.user)
        self.assertEqual(out["status"], "approved")
        self.assertEqual(out["bypass_count"], 0)
        self.assertEqual(len(out["plan_hash"]), 64)

    def test_generated_exam_requires_teacher_knowledge_review(self):
        warnings = [{"code": "knowledge_review_required", "message": "GV phải kiểm duyệt.", "field": ""}]
        with self.assertRaises(agent_bridge.BridgeError) as ctx:
            agent_bridge.publish({"envelope": envelope(warnings=warnings), "approved": True}, self.user)
        self.assertEqual(ctx.exception.code, "knowledge_review_required")
        out = agent_bridge.publish({"envelope": envelope(warnings=warnings), "approved": True,
                                    "reviewed_knowledge": True}, self.user)
        self.assertTrue(out["knowledge_reviewed"])

    def test_edit_after_approval_falls_back_to_draft(self):
        env = envelope()
        approval = agent_bridge.publish({"envelope": env, "approved": True}, self.user)
        same = agent_bridge.review({"envelope": env}, approval)
        self.assertEqual(same["status"], "approved")
        changed = envelope()
        changed["application_plan"]["name"] = "Đổi tên sau duyệt"
        back = agent_bridge.review({"envelope": changed}, approval)
        self.assertEqual(back["status"], "draft")
        self.assertFalse(back["can_publish"])


class SharedCoreCall(unittest.TestCase):
    def test_call_returns_safe_ui_projection_and_draft_hitl(self):
        with mock.patch.dict(os.environ, {"MODEL_PROVIDER": "fake", "AGENT_MODE": "t06_mock"}):
            out = agent_bridge.call({"message": "Tạo game ôn Toán", "session_id": "unit-1"}, case_id="unit-1")
        ui = out["ui"]
        self.assertTrue(ui["html_omitted"])
        self.assertEqual(ui["hitl"]["status"], "draft")
        self.assertFalse(ui["hitl"]["can_publish"])
        self.assertNotIn("html", ui.get("application_plan") or {})
        self.assertIsInstance(out["trace"], dict)


if __name__ == "__main__":
    unittest.main()
