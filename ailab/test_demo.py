"""Chế độ DEMO (nút seed tài khoản ở trang đăng nhập): chỉ store-level, không cần server."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import store  # noqa: E402


class TestDemoLogin(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = store.DB_PATH
        store.DB_PATH = os.path.join(self._tmp.name, "d.db")
        store.init(admin_password="test-admin-pw")

    def tearDown(self):
        store.DB_PATH = self._orig
        self._tmp.cleanup()

    def test_seeds_accounts_with_right_roles_and_is_idempotent(self):
        c = store.connect()
        a1 = store.user_of(c, store.demo_login(c, "admin"))
        a2 = store.user_of(c, store.demo_login(c, "admin"))
        u = store.user_of(c, store.demo_login(c, "user"))
        self.assertEqual((a1["username"], a1["role"]), ("demo_admin", "admin"))
        self.assertEqual(a1["id"], a2["id"])
        self.assertEqual((u["username"], u["role"]), ("demo_user", "user"))
        n = c.execute("SELECT COUNT(*) FROM users WHERE username LIKE 'demo_%'").fetchone()[0]
        self.assertEqual(n, 2)
        c.close()

    def test_unknown_role_rejected_and_password_not_guessable(self):
        c = store.connect()
        with self.assertRaises(store.Err):
            store.demo_login(c, "root")
        store.demo_login(c, "admin")
        for pw in ("demo", "demo_admin", "password", "12345678"):
            with self.assertRaises(store.Err):
                store.login(c, "demo_admin", pw)
        c.close()


if __name__ == "__main__":
    unittest.main()
