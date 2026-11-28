"""Nhúng Chatbot tạo game (edu-game-chatbot): địa chỉ lấy từ AILAB_EDU_CHATBOT_URL, chỉ nhận http(s)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import server  # noqa: E402


class EduChatbotUrl(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.pop("AILAB_EDU_CHATBOT_URL", None)

    def tearDown(self):
        os.environ.pop("AILAB_EDU_CHATBOT_URL", None)
        if self._old is not None:
            os.environ["AILAB_EDU_CHATBOT_URL"] = self._old

    def test_default(self):
        self.assertEqual(server._edu_chatbot_url(), "http://127.0.0.1:8000")

    def test_custom_https(self):
        os.environ["AILAB_EDU_CHATBOT_URL"] = " https://edu.example.vn/chat "
        self.assertEqual(server._edu_chatbot_url(), "https://edu.example.vn/chat")

    def test_reject_unsafe_scheme(self):
        for bad in ("javascript:alert(1)", "file:///etc/passwd", "http://x\"onload=1", "ftp://x"):
            os.environ["AILAB_EDU_CHATBOT_URL"] = bad
            self.assertEqual(server._edu_chatbot_url(), "http://127.0.0.1:8000", bad)


if __name__ == "__main__":
    unittest.main()
