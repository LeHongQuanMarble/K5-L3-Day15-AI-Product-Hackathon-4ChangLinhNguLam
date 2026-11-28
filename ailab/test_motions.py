"""Motion: kịch bản → dựng bài → phiên bản, quyền sở hữu, huỷ. Không cần mạng/model (chế độ giả)."""
import os
import secrets
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["AILAB_DB"] = os.path.join(tempfile.mkdtemp(), "m.db")
os.environ["AILAB_MOTION_STEP_S"] = "0"

import motions  # noqa: E402
import store  # noqa: E402

SCRIPT = "# Bài thử\n\n## Mở bài\nHình: 🎯\n- Ý một\n- Ý hai\nLời: Chào các em.\n\n## Kết\n- Xong\nLời: Hết bài."


class MotionFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store.init("pw-test-12345")
        cls.na, cls.nb = "co_a_" + secrets.token_hex(3), "co_b_" + secrets.token_hex(3)  # DB có thể dùng chung với test khác khi chạy discover
        c = store.connect()
        store.register(c, cls.na, "matkhau123")
        store.register(c, cls.nb, "matkhau123")
        c.close()

    def setUp(self):
        self.c = store.connect()
        self.a = dict(self.c.execute("SELECT * FROM users WHERE username=?", (self.na,)).fetchone())
        self.b = dict(self.c.execute("SELECT * FROM users WHERE username=?", (self.nb,)).fetchone())

    def tearDown(self):
        self.c.close()

    def run_all(self):
        while motions.work_once():
            pass

    def test_parse_script(self):
        title, scenes = motions.parse_script(SCRIPT)
        self.assertEqual(title, "Bài thử")
        self.assertEqual([s["title"] for s in scenes], ["Mở bài", "Kết"])
        self.assertEqual(scenes[0]["icon"], "🎯")
        self.assertEqual(scenes[0]["points"], ["Ý một", "Ý hai"])
        self.assertEqual(scenes[0]["lines"], ["Chào các em."])

    def test_chat_writes_script_then_build_makes_version(self):
        mid = motions.create(self.c, self.a, {"title": "Phân số"})
        motions.ask(self.c, mid, self.a, {"body": "Phân số lớp 4"})
        with self.assertRaises(store.Err):  # đang có yêu cầu mở
            motions.build(self.c, mid, self.a)
        self.run_all()
        m = motions.get(self.c, mid, self.a)
        self.assertIn("## ", m["script"])
        t = motions.thread(self.c, mid, self.a)
        self.assertIsNone(t["open"])
        self.assertEqual([x["kind"] for x in t["messages"]], ["text", "tool", "tool", "tool", "text", "script_changed"])
        motions.build(self.c, mid, self.a)
        self.run_all()
        v = motions.versions(self.c, mid, self.a)
        self.assertEqual(len(v), 1)
        self.assertGreaterEqual(v[0]["scenes"], 3)
        html = motions.version_html(self.c, mid, 1, self.a)
        self.assertIn("<!doctype html>", html)
        motions.build(self.c, mid, self.a)
        self.run_all()
        self.assertEqual(len(motions.versions(self.c, mid, self.a)), 2)

    def test_build_refuses_empty_and_sceneless(self):
        mid = motions.create(self.c, self.a, {"title": "Trống"})
        motions.build(self.c, mid, self.a)
        self.run_all()
        last = motions.thread(self.c, mid, self.a)["messages"][-1]
        self.assertEqual((last["kind"], last["meta"]["code"]), ("build_failed", "empty_script"))
        motions.save_script(self.c, mid, self.a, {"script": "chỉ có chữ, không có cảnh"})
        motions.build(self.c, mid, self.a)
        self.run_all()
        self.assertEqual(motions.thread(self.c, mid, self.a)["messages"][-1]["meta"]["code"], "no_scenes")
        self.assertEqual(motions.versions(self.c, mid, self.a), [])

    def test_script_text_cannot_inject_markup(self):
        mid = motions.create(self.c, self.a, {"title": "Chèn"})
        motions.save_script(self.c, mid, self.a, {"script": "# </script><script>alert(1)</script>\n## A </script><b>\n- <img src=x onerror=1>\nLời: &amp; <i>"})
        motions.build(self.c, mid, self.a)
        self.run_all()
        html = motions.version_html(self.c, mid, 1, self.a)
        body = html.split('id="data">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<", body)
        self.assertNotIn("alert(1)</script>", html)

    def test_owner_only(self):
        mid = motions.create(self.c, self.a, {"title": "Của A"})
        for fn in (lambda: motions.get(self.c, mid, self.b), lambda: motions.thread(self.c, mid, self.b),
                   lambda: motions.ask(self.c, mid, self.b, {"body": "x"}), lambda: motions.build(self.c, mid, self.b)):
            with self.assertRaises(store.Err) as e:
                fn()
            self.assertEqual(e.exception.status, 404)
        self.assertNotIn("Của A", [m["title"] for m in motions.mine(self.c, self.b)])

    def test_cancel_queued(self):
        mid = motions.create(self.c, self.a, {"title": "Huỷ"})
        rid = motions.ask(self.c, mid, self.a, {"body": "gì đó"})
        motions.cancel(self.c, mid, self.a, rid)
        self.assertIsNone(motions.thread(self.c, mid, self.a)["open"])
        self.assertFalse(motions.work_once())
        self.assertEqual(motions.thread(self.c, mid, self.a)["messages"][-1]["kind"], "cancelled")

    def test_delete(self):
        mid = motions.create(self.c, self.a, {"title": "Xoá"})
        motions.delete(self.c, mid, self.a)
        with self.assertRaises(store.Err):
            motions.get(self.c, mid, self.a)


if __name__ == "__main__":
    unittest.main()
